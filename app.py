from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import create_engine
from config import DevelopmentConfig
from models import db
from routes.productos.routes import productos
from routes.usuarios.routes import usuarios  
from routes.clientes.routes import clientes
from routes.categorias.routes import categorias
from routes.pedidos.routes import pedidos
from routes.pagos.routes import pagos


app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

with app.app_context():
    db.create_all()

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
app.config['DB_ENGINE'] = engine
csrf = CSRFProtect(app)
app.register_blueprint(productos)
app.register_blueprint(usuarios)  
app.register_blueprint(clientes)
app.register_blueprint(categorias)
app.register_blueprint(pedidos)
app.register_blueprint(pagos)

@app.route("/")
def inicio():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
