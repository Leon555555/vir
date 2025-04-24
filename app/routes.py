from flask import Blueprint, render_template, jsonify, request, redirect, url_for
from datetime import datetime
import calendar
from .models import Atleta, Entrenamiento
from .extensions import db

main_bp = Blueprint("main", __name__)

# =====================
# PERFIL DEL ATLETA
# =====================

@main_bp.route("/perfil/<int:id>")
def perfil(id):
    atleta = Atleta.query.get_or_404(id)
    entrenamientos = Entrenamiento.query.filter_by(atleta_id=id).order_by(Entrenamiento.fecha).all()
    hoy = datetime.today()

    planificados = [e for e in entrenamientos if e.estado != "realizado"]
    realizados = [e for e in entrenamientos if e.estado == "realizado"]

    primer_dia, num_dias = calendar.monthrange(hoy.year, hoy.month)
    calendario = []
    semana = []

    for i in range(1, primer_dia + 1):
        semana.append(0)

    for dia in range(1, num_dias + 1):
        fecha = datetime(hoy.year, hoy.month, dia).date()
        iconos = []
        entrenamientos_dia = [e for e in entrenamientos if e.fecha == fecha]

        for e in entrenamientos_dia:
            if e.tipo == "run":
                iconos.append("🏃")
            elif e.tipo == "natacion":
                iconos.append("🏊")
            elif e.tipo == "bike":
                iconos.append("🚴")
            elif e.tipo == "fuerza":
                iconos.append("🏋️")
            elif e.tipo == "estirar":
                iconos.append("🧘")
            elif e.tipo == "series":
                iconos.append("🏃‍♂️")

        semana.append({
            "numero": dia,
            "iconos": iconos,
            "bloqueado": entrenamientos_dia[0].bloqueado if entrenamientos_dia else False
        })

        if len(semana) == 7:
            calendario.append(semana)
            semana = []

    if semana:
        while len(semana) < 7:
            semana.append(0)
        calendario.append(semana)

    return render_template("perfil.html",
                           atleta=atleta,
                           entrenamientos_planificados=planificados,
                           entrenamientos_realizados=realizados,
                           calendario_mensual=calendario)

# =====================
# DASHBOARD ENTRENADOR
# =====================

@main_bp.route("/dashboard")
def dashboard():
    atletas = Atleta.query.all()
    nombre = request.args.get("atleta")
    atleta_seleccionado = None
    entrenamientos = []
    calendario_mensual = []

    if nombre:
        atleta = Atleta.query.filter_by(nombre=nombre).first()
        if atleta:
            atleta_seleccionado = atleta.nombre
            entrenamientos = Entrenamiento.query.filter_by(atleta_id=atleta.id).all()

            hoy = datetime.today()
            anio, mes = hoy.year, hoy.month
            primer_dia, num_dias = calendar.monthrange(anio, mes)
            semana = [0] * primer_dia

            for dia in range(1, num_dias + 1):
                semana.append(dia)
                if len(semana) == 7:
                    calendario_mensual.append(semana)
                    semana = []

            if semana:
                while len(semana) < 7:
                    semana.append(0)
                calendario_mensual.append(semana)

    return render_template("dashboard.html",
                           atletas=atletas,
                           entrenamientos=entrenamientos,
                           atleta_seleccionado=atleta_seleccionado,
                           calendario_mensual=calendario_mensual,
                           anio=datetime.today().year,
                           mes=datetime.today().month)

@main_bp.route("/nuevo_entrenamiento", methods=["POST"])
def nuevo_entrenamiento():
    nombre_atleta = request.form.get("atleta")
    fecha = request.form.get("fecha")
    tipo = request.form.get("tipo")
    detalle = request.form.get("detalle")

    atleta = Atleta.query.filter_by(nombre=nombre_atleta).first()

    if atleta:
        nuevo = Entrenamiento(
            atleta_id=atleta.id,
            fecha=datetime.strptime(fecha, "%Y-%m-%d").date(),
            tipo=tipo,
            detalle=detalle,
            estado="pendiente",
            bloqueado=False
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for("main.dashboard", atleta=nombre_atleta))

    return "Atleta no encontrado", 404

# =====================
# FUNCIONES GENERALES
# =====================

@main_bp.route("/guardar_dia", methods=["POST"])
def guardar_dia():
    data = request.get_json()
    dia = data.get("dia")
    tipo = data.get("tipo")
    comentario = data.get("comentario")
    bloqueado = data.get("bloqueado", False)

    hoy = datetime.today()
    fecha = datetime(hoy.year, hoy.month, int(dia)).date()

    entrenamiento = Entrenamiento.query.filter_by(fecha=fecha).first()
    if not entrenamiento:
        return jsonify(success=False, msg="No hay entrenamiento en ese día")

    entrenamiento.tipo = tipo
    entrenamiento.comentario = comentario
    entrenamiento.bloqueado = bloqueado
    db.session.commit()

    return jsonify(success=True)

@main_bp.route("/detalles_dia/<int:dia>")
def detalles_dia(dia):
    hoy = datetime.today()
    fecha = datetime(hoy.year, hoy.month, dia).date()
    entrenamiento = Entrenamiento.query.filter_by(fecha=fecha).first()

    if entrenamiento:
        datos = {
            "tipo": entrenamiento.tipo,
            "comentario": entrenamiento.comentario or "",
            "bloqueado": entrenamiento.bloqueado
        }
    else:
        datos = {"tipo": "", "comentario": "", "bloqueado": False}

    return jsonify(datos)

# =====================
# AUTENTICACIÓN Y NAVEGACIÓN
# =====================

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "lvidelaramos@gmail.com" and password == "1234":
            return redirect(url_for("main.perfil", id=1))
        else:
            error = "Credenciales incorrectas"

    return render_template("login.html", error=error)

@main_bp.route("/")
def index():
    return redirect(url_for("main.login"))

@main_bp.route("/logout")
def logout():
    return redirect(url_for("main.login"))

@main_bp.route("/entrena-en-casa")
def entrena_en_casa():
    return render_template("entrena_en_casa.html")
