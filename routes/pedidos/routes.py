from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import text
from datetime import date
from . import pedidos


def get_db():
    from flask import current_app
    return current_app.config['DB_ENGINE'].connect()


@pedidos.route('/pedidos', methods=['GET'])
def index():
    filtroCliente = request.args.get('cliente', '').strip()
    filtroEstado = request.args.get('estado', 'todos').strip()
    fechaInicio = request.args.get('fecha_inicio', '').strip()
    fechaFin = request.args.get('fecha_fin', '').strip()

    sql = """
        SELECT p.id_pedido, p.fecha, p.total, p.estado,
               c.id_cliente, c.nombre AS cliente_nombre,
               (SELECT COUNT(*) FROM detalle_pedido WHERE id_pedido = p.id_pedido) AS total_productos
        FROM pedidos p
        INNER JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE 1=1
    """
    params = {}

    if filtroCliente:
        sql += " AND c.nombre LIKE :cliente"
        params['cliente'] = f'%{filtroCliente}%'
    
    if filtroEstado != 'todos':
        sql += " AND p.estado = :estado"
        params['estado'] = filtroEstado
    
    if fechaInicio:
        sql += " AND p.fecha >= :fecha_inicio"
        params['fecha_inicio'] = fechaInicio
    
    if fechaFin:
        sql += " AND p.fecha <= :fecha_fin"
        params['fecha_fin'] = fechaFin

    sql += " ORDER BY p.id_pedido DESC"

    with get_db() as conn:
        pedidosRaw = conn.execute(text(sql), params).fetchall()
        clientes = conn.execute(text("SELECT id_cliente, nombre FROM clientes WHERE activo = 1 ORDER BY nombre")).fetchall()
        productos = conn.execute(text("SELECT id_producto, nombre, precio, stock FROM productos WHERE activo = 1 AND stock > 0 ORDER BY nombre")).fetchall()

    pedidos = [dict(p._mapping) for p in pedidosRaw]

    return render_template(
        'pedidos/pedidos.html',
        pedidos=pedidos,
        clientes=clientes,
        productos=productos,
        filtros={
            'cliente': filtroCliente,
            'estado': filtroEstado,
            'fecha_inicio': fechaInicio,
            'fecha_fin': fechaFin,
        }
    )


@pedidos.route('/pedidos/nuevo', methods=['GET'])
def nuevo():
    with get_db() as conn:
        clientes = conn.execute(text("SELECT id_cliente, nombre FROM clientes WHERE activo = 1 ORDER BY nombre")).fetchall()
        productos = conn.execute(text("SELECT id_producto, nombre, precio, stock FROM productos WHERE activo = 1 AND stock > 0 ORDER BY nombre")).fetchall()
    
    return render_template('pedidos/nuevo_pedido.html', clientes=clientes, productos=productos)


@pedidos.route('/pedidos/registrar', methods=['POST'])
def registrar():
    idCliente = request.form.get('id_cliente', '').strip()
    productosJson = request.form.get('productos', '[]')
    
    import json
    productosData = json.loads(productosJson)
    
    if not idCliente or not productosData:
        flash('Seleccione un cliente y al menos un producto.', 'error')
        return redirect(url_for('pedidos.nuevo'))
    
    try:
        with get_db() as conn:
            total = 0
            for item in productosData:
                stockActual = conn.execute(
                    text("SELECT stock FROM productos WHERE id_producto = :id"),
                    {'id': item['id_producto']}
                ).fetchone()
                
                if not stockActual or stockActual[0] < item['cantidad']:
                    flash(f'Stock insuficiente para el producto seleccionado.', 'error')
                    return redirect(url_for('pedidos.nuevo'))
                
                producto = conn.execute(
                    text("SELECT precio FROM productos WHERE id_producto = :id"),
                    {'id': item['id_producto']}
                ).fetchone()
                total += producto[0] * item['cantidad']
            
            fechaActual = date.today()
            result = conn.execute(
                text("""
                    INSERT INTO pedidos (fecha, id_cliente, total, estado)
                    VALUES (:fecha, :id_cliente, :total, 'pendiente')
                """),
                {'fecha': fechaActual, 'id_cliente': idCliente, 'total': total}
            )
            idPedido = result.lastrowid
            
            for item in productosData:
                producto = conn.execute(
                    text("SELECT precio FROM productos WHERE id_producto = :id"),
                    {'id': item['id_producto']}
                ).fetchone()
                
                conn.execute(
                    text("""
                        INSERT INTO detalle_pedido (id_pedido, id_producto, cantidad, precio_unitario)
                        VALUES (:id_pedido, :id_producto, :cantidad, :precio_unitario)
                    """),
                    {
                        'id_pedido': idPedido,
                        'id_producto': item['id_producto'],
                        'cantidad': item['cantidad'],
                        'precio_unitario': producto[0]
                    }
                )
                
                conn.execute(
                    text("UPDATE productos SET stock = stock - :cantidad WHERE id_producto = :id"),
                    {'cantidad': item['cantidad'], 'id': item['id_producto']}
                )
            
            conn.commit()
        
        flash('Pedido registrado correctamente.', 'success')
        return redirect(url_for('pedidos.index'))
    
    except Exception as e:
        flash(f'Error al registrar pedido: {str(e)}', 'error')
        return redirect(url_for('pedidos.nuevo'))


@pedidos.route('/pedidos/ver/<int:id_pedido>')
def ver(id_pedido):
    with get_db() as conn:
        pedido = conn.execute(
            text("""
                SELECT p.id_pedido, p.fecha, p.total, p.estado,
                       c.id_cliente, c.nombre, c.telefono, c.correo, c.direccion
                FROM pedidos p
                INNER JOIN clientes c ON p.id_cliente = c.id_cliente
                WHERE p.id_pedido = :id
            """),
            {'id': id_pedido}
        ).fetchone()
        
        if not pedido:
            return jsonify({'error': 'Pedido no encontrado'}), 404
        
        detalles = conn.execute(
            text("""
                SELECT dp.cantidad, dp.precio_unitario,
                       pr.nombre, (dp.cantidad * dp.precio_unitario) AS subtotal
                FROM detalle_pedido dp
                INNER JOIN productos pr ON dp.id_producto = pr.id_producto
                WHERE dp.id_pedido = :id
            """),
            {'id': id_pedido}
        ).fetchall()
        
        pagos = conn.execute(
            text("""
                SELECT monto, metodo_pago, fecha
                FROM pagos
                WHERE id_pedido = :id
                ORDER BY fecha DESC
            """),
            {'id': id_pedido}
        ).fetchall()
        
        totalPagado = conn.execute(
            text("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE id_pedido = :id"),
            {'id': id_pedido}
        ).fetchone()[0]
        
        saldoPendiente = pedido[2] - totalPagado if pedido[2] else 0
    
    return jsonify({
        'pedido': dict(pedido._mapping),
        'detalles': [dict(d._mapping) for d in detalles],
        'pagos': [dict(p._mapping) for p in pagos],
        'total_pagado': float(totalPagado),
        'saldo_pendiente': float(saldoPendiente)
    })


@pedidos.route('/pedidos/agregarPago', methods=['POST'])
def agregarPago():
    idPedido = request.form.get('id_pedido', '').strip()
    monto = request.form.get('monto', '').strip()
    metodoPago = request.form.get('metodo_pago', '').strip()
    
    if not idPedido or not monto or not metodoPago:
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('pedidos.ver', id_pedido=idPedido))
    
    try:
        monto = float(monto)
        if monto <= 0:
            flash('El monto debe ser mayor a cero.', 'error')
            return redirect(url_for('pedidos.ver', id_pedido=idPedido))
    except ValueError:
        flash('Monto inválido.', 'error')
        return redirect(url_for('pedidos.ver', id_pedido=idPedido))
    
    with get_db() as conn:
        pedido = conn.execute(
            text("SELECT total, estado FROM pedidos WHERE id_pedido = :id"),
            {'id': idPedido}
        ).fetchone()
        
        if not pedido:
            flash('Pedido no encontrado.', 'error')
            return redirect(url_for('pedidos.index'))
        
        totalPagado = conn.execute(
            text("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE id_pedido = :id"),
            {'id': idPedido}
        ).fetchone()[0]
        
        nuevoTotalPagado = totalPagado + monto
        
        if nuevoTotalPagado > pedido[0]:
            flash('El monto excede el total del pedido.', 'error')
            return redirect(url_for('pedidos.ver', id_pedido=idPedido))
        
        fechaActual = date.today()
        conn.execute(
            text("""
                INSERT INTO pagos (id_pedido, monto, metodo_pago, fecha)
                VALUES (:id_pedido, :monto, :metodo_pago, :fecha)
            """),
            {'id_pedido': idPedido, 'monto': monto, 'metodo_pago': metodoPago, 'fecha': fechaActual}
        )
        
        if nuevoTotalPagado >= pedido[0]:
            conn.execute(
                text("UPDATE pedidos SET estado = 'pagado' WHERE id_pedido = :id"),
                {'id': idPedido}
            )
        
        conn.commit()
    
    flash('Pago registrado correctamente.', 'success')
    return redirect(url_for('pedidos.ver', id_pedido=idPedido))


@pedidos.route('/pedidos/cambiarEstado/<int:id_pedido>/<string:estado_actual>', methods=['GET'])
def cambiarEstado(id_pedido, estado_actual):
    nuevoEstado = 'cancelado' if estado_actual == 'pendiente' else 'pendiente'
    
    with get_db() as conn:
        if nuevoEstado == 'cancelado':
            detalles = conn.execute(
                text("SELECT id_producto, cantidad FROM detalle_pedido WHERE id_pedido = :id"),
                {'id': id_pedido}
            ).fetchall()
            
            for detalle in detalles:
                conn.execute(
                    text("UPDATE productos SET stock = stock + :cantidad WHERE id_producto = :id"),
                    {'cantidad': detalle[1], 'id': detalle[0]}
                )
        
        conn.execute(
            text("UPDATE pedidos SET estado = :estado WHERE id_pedido = :id"),
            {'estado': nuevoEstado, 'id': id_pedido}
        )
        conn.commit()
    
    accion = 'cancelado' if nuevoEstado == 'cancelado' else 'reactivado'
    flash(f'Pedido {accion} correctamente.', 'success')
    return redirect(url_for('pedidos.index'))


@pedidos.route('/pedidos/buscarProductos')
def buscarProductos():
    search = request.args.get('search', '').strip()
    
    with get_db() as conn:
        sql = """
            SELECT id_producto, nombre, precio, stock
            FROM productos
            WHERE activo = 1 AND stock > 0
        """
        params = {}
        
        if search:
            sql += " AND nombre LIKE :search"
            params['search'] = f'%{search}%'
        
        sql += " ORDER BY nombre LIMIT 20"
        
        productos = conn.execute(text(sql), params).fetchall()
    
    return jsonify([dict(p._mapping) for p in productos])


@pedidos.route('/pedidos/obtenerCliente/<int:id_cliente>')
def obtenerCliente(id_cliente):
    with get_db() as conn:
        cliente = conn.execute(
            text("SELECT id_cliente, nombre, telefono, correo, direccion FROM clientes WHERE id_cliente = :id AND activo = 1"),
            {'id': id_cliente}
        ).fetchone()
    
    if cliente:
        return jsonify(dict(cliente._mapping))
    return jsonify({'error': 'Cliente no encontrado'}), 404


@pedidos.route('/pedidos/marcarPagado/<int:id_pedido>', methods=['GET'])
def marcarPagado(id_pedido):
    with get_db() as conn:
        pedido = conn.execute(
            text("SELECT total FROM pedidos WHERE id_pedido = :id"),
            {'id': id_pedido}
        ).fetchone()
        
        if not pedido:
            flash('Pedido no encontrado.', 'error')
            return redirect(url_for('pedidos.index'))
        
        fechaActual = date.today()
        conn.execute(
            text("""
                INSERT INTO pagos (id_pedido, monto, metodo_pago, fecha)
                VALUES (:id_pedido, :monto, 'efectivo', :fecha)
            """),
            {'id_pedido': id_pedido, 'monto': pedido[0], 'fecha': fechaActual}
        )
        
        conn.execute(
            text("UPDATE pedidos SET estado = 'pagado' WHERE id_pedido = :id"),
            {'id': id_pedido}
        )
        conn.commit()
    
    flash('Pedido marcado como pagado correctamente.', 'success')
    return redirect(url_for('pedidos.index'))