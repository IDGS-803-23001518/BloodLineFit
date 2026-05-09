from flask import Blueprint

pagos = Blueprint(
    "pagos",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from . import routes  