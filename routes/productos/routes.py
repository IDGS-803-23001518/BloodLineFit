from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import text
import base64
from . import productos


def get_db():
    from flask import current_app
    return current_app.config['DB_ENGINE'].connect()


@productos.route('/productos', methods=['GET'])
def index():
    nombre = request.args.get('nombre', '').strip()
    precio_inicio = request.args.get('precio_inicio', '').strip()
    precio_fin = request.args.get('precio_fin', '').strip()
    id_categoria = request.args.get('id_categoria', '').strip()
    estatus = request.args.get('estatus', 'todos').strip()

    sql = """
        SELECT p.id_producto, p.nombre, p.descripcion, p.precio, p.stock,
               p.imagen, p.activo, c.nombre AS categoria_nombre
        FROM productos p
        LEFT JOIN categorias c ON p.id_categoria = c.id_categoria
        WHERE 1=1
    """
    params = {}

    if nombre:
        sql += " AND p.nombre LIKE :nombre"
        params['nombre'] = f'%{nombre}%'
    if precio_inicio:
        sql += " AND p.precio >= :precio_inicio"
        params['precio_inicio'] = float(precio_inicio)
    if precio_fin:
        sql += " AND p.precio <= :precio_fin"
        params['precio_fin'] = float(precio_fin)
    if id_categoria:
        sql += " AND p.id_categoria = :id_categoria"
        params['id_categoria'] = int(id_categoria)
    if estatus == '1':
        sql += " AND p.activo = 1"
    elif estatus == '0':
        sql += " AND p.activo = 0"

    sql += " ORDER BY p.id_producto DESC"

    with get_db() as conn:
        productos_raw = conn.execute(text(sql), params).fetchall()
        categorias = conn.execute(text("SELECT id_categoria, nombre FROM categorias WHERE activo = 1 ORDER BY nombre")).fetchall()

    productos = []
    for p in productos_raw:
        p_dict = dict(p._mapping)
        if p_dict['imagen'] and isinstance(p_dict['imagen'], (bytes, bytearray)):
            p_dict['imagen'] = base64.b64encode(p_dict['imagen']).decode('utf-8')
        productos.append(p_dict)

    return render_template(
        'productos/productos.html',
        productos=productos,
        categorias=categorias,
        filtros={
            'nombre': nombre,
            'precio_inicio': precio_inicio,
            'precio_fin': precio_fin,
            'id_categoria': id_categoria,
            'estatus': estatus,
        }
    )


@productos.route('/registrar', methods=['POST'])
def registrar():
    nombre = request.form.get('nombre', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    precio = request.form.get('precio', '').strip()
    stock = request.form.get('stock', '0').strip()
    id_categoria = request.form.get('id_categoria', None)
    imagen_file = request.files.get('imagen')

    if not nombre or not precio:
        flash('Nombre y precio son obligatorios.', 'error')
        return redirect(url_for('productos.index'))

    try:
        precio = float(precio)
        stock = int(stock)
    except ValueError:
        flash('Precio o stock inválidos.', 'error')
        return redirect(url_for('productos.index'))

    imagen_b64 = None
    if imagen_file and imagen_file.filename:
        imagen_b64 = base64.b64encode(imagen_file.read()).decode('utf-8')

    id_cat = int(id_categoria) if id_categoria else None

    with get_db() as conn:
        conn.execute(text("""
            INSERT INTO productos (nombre, descripcion, precio, stock, imagen, id_categoria, activo)
            VALUES (:nombre, :descripcion, :precio, :stock, :imagen, :id_categoria, 1)
        """), {
            'nombre': nombre,
            'descripcion': descripcion or None,
            'precio': precio,
            'stock': stock,
            'imagen': imagen_b64,
            'id_categoria': id_cat,
        })
        conn.commit()

    flash('Producto registrado correctamente.', 'success')
    return redirect(url_for('productos.index'))


@productos.route('/productos/editar/<int:id_producto>', methods=['POST'])
def editar(id_producto):
    nombre = request.form.get('nombre', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    precio = request.form.get('precio', '').strip()
    stock = request.form.get('stock', '0').strip()
    id_categoria = request.form.get('id_categoria', None)
    imagen_file = request.files.get('imagen')

    if not nombre or not precio:
        flash('Nombre y precio son obligatorios.', 'error')
        return redirect(url_for('productos.index'))

    try:
        precio = float(precio)
        stock = int(stock)
    except ValueError:
        flash('Precio o stock inválidos.', 'error')
        return redirect(url_for('productos.index'))

    id_cat = int(id_categoria) if id_categoria else None

    with get_db() as conn:
        if imagen_file and imagen_file.filename:
            imagen_b64 = base64.b64encode(imagen_file.read()).decode('utf-8')
            conn.execute(text("""
                UPDATE productos
                SET nombre=:nombre, descripcion=:descripcion, precio=:precio,
                    stock=:stock, imagen=:imagen, id_categoria=:id_categoria
                WHERE id_producto=:id
            """), {
                'nombre': nombre, 'descripcion': descripcion or None,
                'precio': precio, 'stock': stock,
                'imagen': imagen_b64, 'id_categoria': id_cat, 'id': id_producto,
            })
        else:
            conn.execute(text("""
                UPDATE productos
                SET nombre=:nombre, descripcion=:descripcion, precio=:precio,
                    stock=:stock, id_categoria=:id_categoria
                WHERE id_producto=:id
            """), {
                'nombre': nombre, 'descripcion': descripcion or None,
                'precio': precio, 'stock': stock,
                'id_categoria': id_cat, 'id': id_producto,
            })
        conn.commit()

    flash('Producto actualizado correctamente.', 'success')
    return redirect(url_for('productos.index'))


@productos.route('/productos/estatus/<int:id_producto>/<int:estatus_actual>', methods=['GET'])
def cambiar_estatus(id_producto, estatus_actual):
    nuevo_estatus = 0 if estatus_actual == 1 else 1
    with get_db() as conn:
        conn.execute(
            text("UPDATE productos SET activo = :activo WHERE id_producto = :id"),
            {'activo': nuevo_estatus, 'id': id_producto}
        )
        conn.commit()

    accion = 'desactivado' if nuevo_estatus == 0 else 'activado'
    flash(f'Producto {accion} correctamente.', 'success')
    return redirect(url_for('productos.index'))