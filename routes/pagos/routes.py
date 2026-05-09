from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy import text
from datetime import datetime
import locale
from . import pagos

# Configuración de idioma (si falla en tu sistema, puedes comentar esta línea)
try:
    locale.setlocale(locale.LC_TIME, 'es_MX.UTF-8')
except:
    pass

MESES = [
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
]


def fecha_es(d):
    if not d:
        return ''

    # Si viene como string desde la BD
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, '%Y-%m-%d')
        except ValueError:
            return d

    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


def get_db():
    from flask import current_app
    return current_app.config['DB_ENGINE'].connect()


@pagos.route('/pagos', methods=['GET'])
def index():
    filtroCliente = request.args.get('cliente', '').strip()
    filtroMetodo = request.args.get('metodo', 'todos').strip()
    filtroIdPedido = request.args.get('id_pedido', '').strip()
    fechaInicio = request.args.get('fecha_inicio', '').strip()
    fechaFin = request.args.get('fecha_fin', '').strip()

    sql = """
        SELECT pg.id_pago, pg.id_pedido, pg.monto, pg.metodo_pago, pg.fecha,
               c.nombre AS cliente_nombre
        FROM pagos pg
        INNER JOIN pedidos p ON pg.id_pedido = p.id_pedido
        INNER JOIN clientes c ON p.id_cliente = c.id_cliente
        WHERE 1=1
    """

    params = {}

    if filtroIdPedido:
        sql += " AND pg.id_pedido = :id_pedido"
        params['id_pedido'] = filtroIdPedido

    if filtroCliente:
        sql += " AND c.nombre LIKE :cliente"
        params['cliente'] = f'%{filtroCliente}%'

    if filtroMetodo != 'todos':
        sql += " AND pg.metodo_pago = :metodo"
        params['metodo'] = filtroMetodo

    if fechaInicio:
        sql += " AND pg.fecha >= :fecha_inicio"
        params['fecha_inicio'] = fechaInicio

    if fechaFin:
        sql += " AND pg.fecha <= :fecha_fin"
        params['fecha_fin'] = fechaFin

    sql += " ORDER BY pg.id_pago DESC"

    with get_db() as conn:
        pagosRaw = conn.execute(text(sql), params).fetchall()

        pedidos_pendientes = conn.execute(text("""
            SELECT p.id_pedido, p.total, c.nombre AS cliente_nombre,
                   COALESCE(
                       (SELECT SUM(monto) FROM pagos WHERE id_pedido = p.id_pedido),
                       0
                   ) AS total_pagado
            FROM pedidos p
            INNER JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE p.estado = 'pendiente'
            HAVING (p.total - total_pagado) > 0
            ORDER BY p.id_pedido DESC
        """)).fetchall()

    pagos_list = []

    for p in pagosRaw:
        row = dict(p._mapping)
        row['fecha'] = fecha_es(row['fecha'])
        pagos_list.append(row)

    return render_template(
        'pagos/pagos.html',
        pagos=pagos_list,
        pedidos_pendientes=[dict(p._mapping) for p in pedidos_pendientes],
        filtros={
            'cliente': filtroCliente,
            'metodo': filtroMetodo,
            'id_pedido': filtroIdPedido,
            'fecha_inicio': fechaInicio,
            'fecha_fin': fechaFin,
        }
    )


@pagos.route('/pagos/registrar', methods=['POST'])
def registrar():
    idPedido = request.form.get('id_pedido', '').strip()
    montoStr = request.form.get('monto', '').strip()
    metodoPago = request.form.get('metodo_pago', '').strip()

    if not idPedido or not montoStr or not metodoPago:
        flash('Todos los campos son obligatorios.', 'error')
        return redirect(url_for('pagos.index'))

    try:
        monto = float(montoStr)
        if monto <= 0:
            raise ValueError
    except ValueError:
        flash('El monto debe ser un número mayor a cero.', 'error')
        return redirect(url_for('pagos.index'))

    metodos_validos = ('efectivo', 'tarjeta', 'transferencia')

    if metodoPago not in metodos_validos:
        flash('Método de pago no válido.', 'error')
        return redirect(url_for('pagos.index'))

    with get_db() as conn:
        pedido = conn.execute(
            text("SELECT id_pedido, total, estado FROM pedidos WHERE id_pedido = :id"),
            {'id': idPedido}
        ).fetchone()

        if not pedido:
            flash('El pedido no fue encontrado.', 'error')
            return redirect(url_for('pagos.index'))

        if pedido.estado != 'pendiente':
            flash('Solo se pueden registrar pagos en pedidos con estado pendiente.', 'error')
            return redirect(url_for('pagos.index'))

        total_pagado = conn.execute(
            text("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE id_pedido = :id"),
            {'id': idPedido}
        ).fetchone()[0]

        saldo_pendiente = float(pedido.total) - float(total_pagado)

        if monto > saldo_pendiente:
            flash(
                f'El monto ingresado (${monto:.2f}) supera el saldo pendiente del pedido (${saldo_pendiente:.2f}).',
                'error'
            )
            return redirect(url_for('pagos.index'))

        conn.execute(
            text("""
                INSERT INTO pagos (id_pedido, monto, metodo_pago, fecha)
                VALUES (:id_pedido, :monto, :metodo_pago, :fecha)
            """),
            {
                'id_pedido': idPedido,
                'monto': monto,
                'metodo_pago': metodoPago,
                'fecha': datetime.now().date()
            }
        )

        nuevo_total_pagado = float(total_pagado) + monto

        if nuevo_total_pagado >= float(pedido.total):
            conn.execute(
                text("UPDATE pedidos SET estado = 'pagado' WHERE id_pedido = :id"),
                {'id': idPedido}
            )

        conn.commit()

    flash('Pago registrado correctamente.', 'success')
    return redirect(url_for('pagos.index'))


@pagos.route('/pagos/ver/<int:id_pago>')
def ver(id_pago):
    with get_db() as conn:
        pago = conn.execute(
            text("""
                SELECT pg.id_pago, pg.id_pedido, pg.monto, pg.metodo_pago, pg.fecha,
                       c.nombre AS cliente_nombre
                FROM pagos pg
                INNER JOIN pedidos p ON pg.id_pedido = p.id_pedido
                INNER JOIN clientes c ON p.id_cliente = c.id_cliente
                WHERE pg.id_pago = :id
            """),
            {'id': id_pago}
        ).fetchone()

        if not pago:
            return jsonify({'error': 'Pago no encontrado'}), 404

        pedido = conn.execute(
            text("SELECT id_pedido, total, estado FROM pedidos WHERE id_pedido = :id"),
            {'id': pago.id_pedido}
        ).fetchone()

        total_pagado = conn.execute(
            text("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE id_pedido = :id"),
            {'id': pago.id_pedido}
        ).fetchone()[0]

        saldo_pendiente = float(pedido.total) - float(total_pagado)

    pago_dict = dict(pago._mapping)
    pago_dict['fecha'] = fecha_es(pago_dict['fecha'])

    return jsonify({
        'pago': pago_dict,
        'pedido': dict(pedido._mapping),
        'total_pagado': float(total_pagado),
        'saldo_pendiente': float(saldo_pendiente)
    })


@pagos.route('/pagos/eliminar/<int:id_pago>')
def eliminar(id_pago):
    with get_db() as conn:
        pago = conn.execute(
            text("SELECT id_pago, id_pedido, monto FROM pagos WHERE id_pago = :id"),
            {'id': id_pago}
        ).fetchone()

        if not pago:
            flash('El pago no fue encontrado.', 'error')
            return redirect(url_for('pagos.index'))

        conn.execute(
            text("DELETE FROM pagos WHERE id_pago = :id"),
            {'id': id_pago}
        )

        nuevo_total_pagado = conn.execute(
            text("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE id_pedido = :id"),
            {'id': pago.id_pedido}
        ).fetchone()[0]

        pedido = conn.execute(
            text("SELECT total FROM pedidos WHERE id_pedido = :id"),
            {'id': pago.id_pedido}
        ).fetchone()

        if float(nuevo_total_pagado) < float(pedido.total):
            conn.execute(
                text("UPDATE pedidos SET estado = 'pendiente' WHERE id_pedido = :id"),
                {'id': pago.id_pedido}
            )

        conn.commit()

    flash(
        'Pago eliminado correctamente. El pedido fue revertido a pendiente si correspondía.',
        'success'
    )

    return redirect(url_for('pagos.index'))


@pagos.route('/pagos/editar', methods=['POST'])
def editar():
    idPago = request.form.get('id_pago', '').strip()
    metodoPago = request.form.get('metodo_pago', '').strip()

    metodos_validos = ('efectivo', 'tarjeta', 'transferencia')

    if not idPago or metodoPago not in metodos_validos:
        flash('Datos inválidos para editar el pago.', 'error')
        return redirect(url_for('pagos.index'))

    with get_db() as conn:
        pago = conn.execute(
            text("SELECT id_pago FROM pagos WHERE id_pago = :id"),
            {'id': idPago}
        ).fetchone()

        if not pago:
            flash('El pago no fue encontrado.', 'error')
            return redirect(url_for('pagos.index'))

        conn.execute(
            text("""
                UPDATE pagos
                SET metodo_pago = :metodo
                WHERE id_pago = :id
            """),
            {
                'metodo': metodoPago,
                'id': idPago
            }
        )

        conn.commit()

    flash('Método de pago actualizado correctamente.', 'success')
    return redirect(url_for('pagos.index'))