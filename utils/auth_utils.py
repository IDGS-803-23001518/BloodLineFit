from functools import wraps
from flask import request, redirect, url_for, current_app
import jwt


def get_usuario_actual():
    """
    Decodifica el token de la cookie y retorna el payload,
    o None si no hay token válido.
    """
    token = request.cookies.get('token')
    if not token:
        return None
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        usuario = get_usuario_actual()
        if not usuario:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated