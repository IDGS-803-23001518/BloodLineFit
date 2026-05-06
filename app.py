from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import create_engine
from config import DevelopmentConfig
from models import db
from routes.productos import productos
from routes.categorias.routes import categorias

app = Flask(__name__)
app.config.from_object(DevelopmentConfig)
db.init_app(app)

with app.app_context():
    db.create_all()

engine = create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
app.config['DB_ENGINE'] = engine
csrf = CSRFProtect(app)
app.register_blueprint(productos)
app.register_blueprint(categorias)

@app.route("/")
def inicio():
    return render_template("index.html")

if __name__ == '__main__':
    app.run(debug=True)
