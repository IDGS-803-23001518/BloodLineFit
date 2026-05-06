from flask import flash, redirect, render_template, request, url_for
from sqlalchemy import text

from . import categorias


def get_db():
    from flask import current_app
    return current_app.config["DB_ENGINE"].connect()


@categorias.route("/categorias", methods=["GET"])
def listado_categorias():
    nombre = request.args.get("nombre", "").strip()
    estatus = request.args.get("estatus", "todos").strip()

    sql = "SELECT id_categoria, nombre, activo FROM categorias WHERE 1=1"
    params = {}

    if nombre:
        sql += " AND nombre LIKE :nombre"
        params["nombre"] = f"%{nombre}%"
    if estatus == "1":
        sql += " AND activo = 1"
    elif estatus == "0":
        sql += " AND activo = 0"

    sql += " ORDER BY id_categoria DESC"

    with get_db() as conn:
        categorias_list = conn.execute(text(sql), params).fetchall()

    categorias_data = [dict(categoria._mapping) for categoria in categorias_list]

    return render_template(
        "categorias/categorias.html",
        categorias=categorias_data,
        filtros={"nombre": nombre, "estatus": estatus},
    )


@categorias.route("/registrar-categoria", methods=["POST"])
def registrar_categoria():
    nombre = request.form.get("nombre", "").strip()

    if not nombre:
        flash("El nombre es obligatorio.", "error")
        return redirect(url_for("categorias.listado_categorias"))

    with get_db() as conn:
        conn.execute(
            text("INSERT INTO categorias (nombre, activo) VALUES (:nombre, 1)"),
            {"nombre": nombre},
        )
        conn.commit()

    flash("Categoria registrada correctamente.", "success")
    return redirect(url_for("categorias.listado_categorias"))


@categorias.route("/editar-categoria/<int:id_categoria>", methods=["POST"])
def editar_categoria(id_categoria):
    nombre = request.form.get("nombre", "").strip()

    if not nombre:
        flash("El nombre es obligatorio.", "error")
        return redirect(url_for("categorias.listado_categorias"))

    with get_db() as conn:
        conn.execute(
            text("UPDATE categorias SET nombre = :nombre WHERE id_categoria = :id"),
            {"nombre": nombre, "id": id_categoria},
        )
        conn.commit()

    flash("Categoria actualizada correctamente.", "success")
    return redirect(url_for("categorias.listado_categorias"))


@categorias.route(
    "/cambiar-estatus-categoria/<int:id_categoria>/<int:estatus_actual>",
    methods=["GET"],
)
def cambiar_estatus_categoria(id_categoria, estatus_actual):
    nuevo_estatus = 0 if estatus_actual == 1 else 1

    with get_db() as conn:
        conn.execute(
            text("UPDATE categorias SET activo = :activo WHERE id_categoria = :id"),
            {"activo": nuevo_estatus, "id": id_categoria},
        )
        conn.commit()

    accion = "desactivada" if nuevo_estatus == 0 else "activada"
    flash(f"Categoria {accion} correctamente.", "success")
    return redirect(url_for("categorias.listado_categorias"))
