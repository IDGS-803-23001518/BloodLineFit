from flask import Blueprint, render_template, request, redirect, url_for, flash
from sqlalchemy import text
from . import clientes


def get_db():
    from flask import current_app
    return current_app.config['DB_ENGINE'].connect()


@clientes.route('/clientes', methods=['GET'])
def index():
    nombre = request.args.get('nombre', '').strip()
    telefono = request.args.get('telefono', '').strip()
    correo = request.args.get('correo', '').strip()
    estatus = request.args.get('estatus', 'todos').strip()

    sql = "SELECT id_cliente, nombre, telefono, correo, direccion, activo FROM clientes WHERE 1=1"
    params = {}

    if nombre:
        sql += " AND nombre LIKE :nombre"
        params['nombre'] = f'%{nombre}%'
    if telefono:
        sql += " AND telefono LIKE :telefono"
        params['telefono'] = f'%{telefono}%'
    if correo:
        sql += " AND correo LIKE :correo"
        params['correo'] = f'%{correo}%'
    if estatus == '1':
        sql += " AND activo = 1"
    elif estatus == '0':
        sql += " AND activo = 0"

    sql += " ORDER BY activo DESC, id_cliente DESC"

    with get_db() as conn:
        clientes_raw = conn.execute(text(sql), params).fetchall()

    clientes_list = [dict(c._mapping) for c in clientes_raw]

    return render_template(
        'clientes/clientes.html',
        clientes=clientes_list,
        filtros={
            'nombre': nombre,
            'telefono': telefono,
            'correo': correo,
            'estatus': estatus,
        }
    )


@clientes.route('/clientes/registrar', methods=['POST'])
def registrar():
    nombre = request.form.get('nombre', '').strip()
    telefono = request.form.get('telefono', '').strip()
    correo = request.form.get('correo', '').strip()
    direccion = request.form.get('direccion', '').strip()

    if not nombre:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('clientes.index'))

    with get_db() as conn:
        conn.execute(text("""
            INSERT INTO clientes (nombre, telefono, correo, direccion, activo)
            VALUES (:nombre, :telefono, :correo, :direccion, 1)
        """), {
            'nombre': nombre,
            'telefono': telefono or None,
            'correo': correo or None,
            'direccion': direccion or None,
        })
        conn.commit()

    flash('Cliente registrado correctamente.', 'success')
    return redirect(url_for('clientes.index'))


@clientes.route('/clientes/editar/<int:id_cliente>', methods=['POST'])
def editar(id_cliente):
    nombre = request.form.get('nombre', '').strip()
    telefono = request.form.get('telefono', '').strip()
    correo = request.form.get('correo', '').strip()
    direccion = request.form.get('direccion', '').strip()

    if not nombre:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('clientes.index'))

    with get_db() as conn:
        conn.execute(text("""
            UPDATE clientes
            SET nombre=:nombre, telefono=:telefono, correo=:correo, direccion=:direccion
            WHERE id_cliente=:id
        """), {
            'nombre': nombre,
            'telefono': telefono or None,
            'correo': correo or None,
            'direccion': direccion or None,
            'id': id_cliente,
        })
        conn.commit()

    flash('Cliente actualizado correctamente.', 'success')
    return redirect(url_for('clientes.index'))


@clientes.route('/clientes/estatus/<int:id_cliente>/<int:estatus_actual>', methods=['GET'])
def cambiar_estatus(id_cliente, estatus_actual):
    nuevo_estatus = 0 if estatus_actual == 1 else 1
    with get_db() as conn:
        conn.execute(
            text("UPDATE clientes SET activo = :activo WHERE id_cliente = :id"),
            {'activo': nuevo_estatus, 'id': id_cliente}
        )
        conn.commit()

    accion = 'desactivado' if nuevo_estatus == 0 else 'activado'
    flash(f'Cliente {accion} correctamente.', 'success')
    return redirect(url_for('clientes.index'))
