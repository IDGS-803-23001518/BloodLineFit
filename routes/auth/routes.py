from flask import render_template, request, redirect, url_for, flash, make_response, current_app
from sqlalchemy import text
from werkzeug.security import check_password_hash
import jwt
import datetime
from . import auth


def get_db():
    return current_app.config['DB_ENGINE'].connect()


def get_usuario_actual():
    token = request.cookies.get('token')
    if not token:
        return None
    try:
        return jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


@auth.route('/login', methods=['GET'])
def login():
    if get_usuario_actual():
        return redirect(url_for('inicio'))      # ya tiene sesión → dashboard
    return render_template('auth/login.html')   # sin sesión → muestra el form


@auth.route('/login', methods=['POST'])
def login_post():
    nombre_usuario = request.form.get('nombre_usuario', '').strip()
    contrasena     = request.form.get('contrasena', '')

    if not nombre_usuario or not contrasena:
        flash('Usuario y contraseña son obligatorios.', 'error')
        return redirect(url_for('auth.login'))

    with get_db() as conn:
        usuario = conn.execute(
            text("SELECT id_usuario, nombre_usuario, contrasena, activo FROM usuarios WHERE nombre_usuario = :nombre"),
            {'nombre': nombre_usuario}
        ).fetchone()

    if not usuario:
        flash('Usuario o contraseña incorrectos.', 'error')
        return redirect(url_for('auth.login'))

    u = dict(usuario._mapping)

    if not u['activo']:
        flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
        return redirect(url_for('auth.login'))

    if not check_password_hash(u['contrasena'], contrasena):
        flash('Usuario o contraseña incorrectos.', 'error')
        return redirect(url_for('auth.login'))

    payload = {
        'id_usuario':     u['id_usuario'],
        'nombre_usuario': u['nombre_usuario'],
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    }
    token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

    response = make_response(redirect(url_for('inicio')))
    response.set_cookie('token', token, httponly=True, samesite='Lax', max_age=8 * 3600)
    return response


@auth.route('/logout')
def logout():
    response = make_response(redirect(url_for('auth.login')))
    response.delete_cookie('token')
    return response