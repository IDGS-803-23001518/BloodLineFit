from flask import Blueprint

pedidos = Blueprint(
    "pedidos",
    __name__,
    template_folder="templates",
    static_folder="static",
)
