from flask_sqlalchemy import SQLAlchemy
import enum

db = SQLAlchemy()

class EstadoPedidoEnum(enum.Enum):
    pendiente = 'pendiente'
    pagado = 'pagado'
    cancelado = 'cancelado'


class MetodoPagoEnum(enum.Enum):
    efectivo = 'efectivo'
    tarjeta = 'tarjeta'
    transferencia = 'transferencia'

class Categoria(db.Model):
    __tablename__ = 'categorias'

    id_categoria = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    activo = db.Column(db.Boolean, default=True)

    productos = db.relationship('Producto', backref='categoria', lazy=True)

    def __repr__(self):
        return f'<Categoria {self.nombre}>'


class Producto(db.Model):
    __tablename__ = 'productos'

    id_producto = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    imagen = db.Column(db.Text(length=16777215))
    id_categoria = db.Column(db.Integer, db.ForeignKey('categorias.id_categoria'))
    activo = db.Column(db.Boolean, default=True)

    detalles = db.relationship('DetallePedido', backref='producto', lazy=True)

    def __repr__(self):
        return f'<Producto {self.nombre}>'


class Cliente(db.Model):
    __tablename__ = 'clientes'

    id_cliente = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20))
    correo = db.Column(db.String(100))
    direccion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)

    pedidos = db.relationship('Pedido', backref='cliente', lazy=True)

    def __repr__(self):
        return f'<Cliente {self.nombre}>'


class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id_usuario = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nombre_usuario = db.Column(db.String(50), unique=True, nullable=False)
    contrasena = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(100))
    activo = db.Column(db.Boolean, default=True)

    def __repr__(self):
        return f'<Usuario {self.nombre_usuario}>'


class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id_pedido = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fecha = db.Column(db.Date, nullable=False)
    id_cliente = db.Column(db.Integer, db.ForeignKey('clientes.id_cliente'), nullable=False)
    total = db.Column(db.Numeric(10, 2), default=0.00)
    estado = db.Column(db.Enum(EstadoPedidoEnum), default=EstadoPedidoEnum.pendiente)

    detalles = db.relationship('DetallePedido', backref='pedido', lazy=True)
    pagos = db.relationship('Pago', backref='pedido', lazy=True)

    def __repr__(self):
        return f'<Pedido {self.id_pedido}>'


class DetallePedido(db.Model):
    __tablename__ = 'detalle_pedido'

    id_detalle = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedidos.id_pedido'), nullable=False)
    id_producto = db.Column(db.Integer, db.ForeignKey('productos.id_producto'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<DetallePedido pedido={self.id_pedido} producto={self.id_producto}>'


class Pago(db.Model):
    __tablename__ = 'pagos'

    id_pago = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_pedido = db.Column(db.Integer, db.ForeignKey('pedidos.id_pedido'), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    metodo_pago = db.Column(db.Enum(MetodoPagoEnum), nullable=False)
    fecha = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f'<Pago {self.id_pago}>'