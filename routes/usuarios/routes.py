from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from sqlalchemy import text
from werkzeug.security import generate_password_hash, check_password_hash
from utils.auth_utils import login_required
from . import usuarios


def get_db():
    from flask import current_app
    return current_app.config['DB_ENGINE'].connect()


@usuarios.route('/usuarios', methods=['GET'])
@login_required
def index():
    nombre_usuario = request.args.get('nombre_usuario', '').strip()
    email = request.args.get('email', '').strip()
    estatus = request.args.get('estatus', 'todos').strip()

    sql = """
        SELECT id_usuario, nombre_usuario, email, activo
        FROM usuarios
        WHERE 1=1
    """
    params = {}

    if nombre_usuario:
        sql += " AND nombre_usuario LIKE :nombre_usuario"
        params['nombre_usuario'] = f'%{nombre_usuario}%'
    if email:
        sql += " AND email LIKE :email"
        params['email'] = f'%{email}%'
    if estatus == '1':
        sql += " AND activo = 1"
    elif estatus == '0':
        sql += " AND activo = 0"

    sql += " ORDER BY id_usuario DESC"

    with get_db() as conn:
        usuarios_raw = conn.execute(text(sql), params).fetchall()

    usuarios_lista = []
    for u in usuarios_raw:
        usuarios_lista.append(dict(u._mapping))

    return render_template(
        'usuarios/usuarios.html',
        usuarios=usuarios_lista,
        filtros={
            'nombre_usuario': nombre_usuario,
            'email': email,
            'estatus': estatus,
        }
    )


@usuarios.route('/usuarios/registrar', methods=['POST'])
@login_required
def registrar():
    nombre_usuario = request.form.get('nombre_usuario', '').strip()
    contrasena = request.form.get('contrasena', '')
    email = request.form.get('email', '').strip() or None

    if not nombre_usuario or not contrasena:
        flash('Nombre de usuario y contraseña son obligatorios.', 'error')
        return redirect(url_for('usuarios.index'))

    if len(contrasena) < 6:
        flash('La contraseña debe tener al menos 6 caracteres.', 'error')
        return redirect(url_for('usuarios.index'))

    with get_db() as conn:
        exists = conn.execute(
            text("SELECT id_usuario FROM usuarios WHERE nombre_usuario = :nombre"),
            {'nombre': nombre_usuario}
        ).fetchone()

        if exists:
            flash('El nombre de usuario ya existe. Por favor, elige otro.', 'error')
            return redirect(url_for('usuarios.index'))

        hashed_password = generate_password_hash(contrasena)

        conn.execute(text("""
            INSERT INTO usuarios (nombre_usuario, contrasena, email, activo)
            VALUES (:nombre_usuario, :contrasena, :email, 1)
        """), {
            'nombre_usuario': nombre_usuario,
            'contrasena': hashed_password,
            'email': email,
        })
        conn.commit()

    flash('Usuario registrado correctamente.', 'success')
    return redirect(url_for('usuarios.index'))


@usuarios.route('/usuarios/editar/<int:id_usuario>', methods=['POST'])
@login_required
def editar(id_usuario):
    nombre_usuario = request.form.get('nombre_usuario', '').strip()
    email = request.form.get('email', '').strip() or None
    nueva_contrasena = request.form.get('nueva_contrasena', '')

    if not nombre_usuario:
        flash('El nombre de usuario es obligatorio.', 'error')
        return redirect(url_for('usuarios.index'))

    with get_db() as conn:
        exists = conn.execute(
            text("SELECT id_usuario FROM usuarios WHERE nombre_usuario = :nombre AND id_usuario != :id"),
            {'nombre': nombre_usuario, 'id': id_usuario}
        ).fetchone()

        if exists:
            flash('El nombre de usuario ya está en uso por otro usuario.', 'error')
            return redirect(url_for('usuarios.index'))

        if nueva_contrasena:
            if len(nueva_contrasena) < 6:
                flash('La contraseña debe tener al menos 6 caracteres.', 'error')
                return redirect(url_for('usuarios.index'))
            hashed_password = generate_password_hash(nueva_contrasena)
            conn.execute(text("""
                UPDATE usuarios
                SET nombre_usuario = :nombre_usuario, contrasena = :contrasena, email = :email
                WHERE id_usuario = :id
            """), {
                'nombre_usuario': nombre_usuario,
                'contrasena': hashed_password,
                'email': email,
                'id': id_usuario,
            })
        else:
            conn.execute(text("""
                UPDATE usuarios
                SET nombre_usuario = :nombre_usuario, email = :email
                WHERE id_usuario = :id
            """), {
                'nombre_usuario': nombre_usuario,
                'email': email,
                'id': id_usuario,
            })
        conn.commit()

    flash('Usuario actualizado correctamente.', 'success')
    return redirect(url_for('usuarios.index'))


@usuarios.route('/usuarios/estatus/<int:id_usuario>/<int:estatus_actual>', methods=['GET'])
@login_required
def cambiar_estatus(id_usuario, estatus_actual):
    nuevo_estatus = 0 if estatus_actual == 1 else 1
    with get_db() as conn:
        conn.execute(
            text("UPDATE usuarios SET activo = :activo WHERE id_usuario = :id"),
            {'activo': nuevo_estatus, 'id': id_usuario}
        )
        conn.commit()

    accion = 'desactivado' if nuevo_estatus == 0 else 'activado'
    flash(f'Usuario {accion} correctamente.', 'success')
    return redirect(url_for('usuarios.index'))


@usuarios.route('/usuarios/ver/<int:id_usuario>', methods=['GET'])
@login_required
def ver(id_usuario):
    with get_db() as conn:
        usuario = conn.execute(
            text("SELECT id_usuario, nombre_usuario, email, activo FROM usuarios WHERE id_usuario = :id"),
            {'id': id_usuario}
        ).fetchone()

    if not usuario:
        return {'error': 'Usuario no encontrado'}, 404

    return dict(usuario._mapping)