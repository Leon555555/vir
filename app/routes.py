from datetime import date, datetime, timedelta
import calendar
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

bp = Blueprint("main", __name__)
main_bp = bp  # alias para __init__.py

# =========================
# DATOS DEMO EN MEMORIA
# =========================
_ATLETAS = [
    {
        "id": str(uuid.uuid4()),
        "nombre": "Leo Videla",
        "email": "leo@ua.test",
        "telefono": "+34 600 000 000",
        "edad": 30,
        "altura": 175,
        "peso": 70,
    }
]

class _VMAtleta:
    def __init__(self, nombre): 
        self.nombre = nombre

class _VMEntrenamiento:
    def __init__(self, atleta_nombre: str, fecha_dt: datetime, tipo: str, detalle: str):
        self.id = str(uuid.uuid4())
        self.fecha = fecha_dt
        self.tipo = tipo
        self.detalle = detalle
        self.atleta = _VMAtleta(atleta_nombre)
        self.bloqueado = False

_ENTRENAMIENTOS = []


def _seed_demo():
    """Genera datos de entrenamiento demo solo la primera vez."""
    if _ENTRENAMIENTOS:
        return
    hoy = date.today()
    nombre = _ATLETAS[0]["nombre"]
    demo = [
        (2, "Run", "Rodaje suave 6k"),
        (5, "Fuerza", "Full body 45’"),
        (9, "Estiramientos", "Movilidad + core 25’"),
    ]
    for d, t, det in demo:
        try:
            _ENTRENAMIENTOS.append(
                _VMEntrenamiento(nombre, datetime(hoy.year, hoy.month, d, 18, 0, 0), t, det)
            )
        except ValueError:
            pass

_seed_demo()

# =========================
# HELPERS
# =========================
def _build_month_matrix(year: int, month: int):
    cal = calendar.Calendar(firstweekday=0)
    days = list(cal.itermonthdays(year, month))
    weeks = [days[i:i + 7] for i in range(0, len(days), 7)]
    while len(weeks) < 6:
        weeks.append([0] * 7)
    return weeks[:6]


def _weeks_with_flag(year: int, month: int, today: date):
    base = _build_month_matrix(year, month)
    semanas = []
    for w in base:
        es_actual = (today.year == year and today.month == month and today.day in w)
        semanas.append({"dias": w, "es_actual": es_actual})
    return semanas


def _find_atleta_by_id(atleta_id: str):
    return next((a for a in _ATLETAS if a["id"] == atleta_id), None)


# =========================
# RUTAS
# =========================
@main_bp.get("/")
def dashboard_entrenador():
    return redirect(url_for("main.perfil", id=_ATLETAS[0]["id"]))


@main_bp.get("/perfil/<id>")
def perfil(id):
    atleta = _find_atleta_by_id(id)
    if not atleta:
        flash("Atleta no encontrado", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    hoy = date.today()
    realizados = [e for e in _ENTRENAMIENTOS if e.atleta.nombre == atleta["nombre"]]
    planificados = 5
    total = len(realizados) + planificados
    progreso = (len(realizados) / total * 100) if total > 0 else 0

    # Mes y calendario
    anio = int(request.args.get("anio", hoy.year))
    mes = int(request.args.get("mes", hoy.month))
    semanas = _weeks_with_flag(anio, mes, hoy)
    meses = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio",
             "Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
    mes_label = f"{meses[mes-1]} {anio}"

    # Entrenamientos del mes
    entrenos_mes = [
        e for e in _ENTRENAMIENTOS
        if e.atleta.nombre == atleta["nombre"] and e.fecha.year == anio and e.fecha.month == mes
    ]

    # ======== NUEVO: Resumen semanal dinámico ========
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    semana = [
        e for e in _ENTRENAMIENTOS
        if e.atleta.nombre == atleta["nombre"] and inicio_semana <= e.fecha.date() <= fin_semana
    ]
    minutos = len(semana) * 45
    km = sum(8 if e.tipo == "Run" else 0 for e in semana)
    resumen = {"semanales": len(semana), "minutos": minutos, "km": km}
    # ==================================================

    return render_template(
        "perfil.html",
        atleta=atleta,
        entrenamientos_realizados=realizados,
        entrenamientos_planificados=planificados,
        progreso=progreso,
        semanas=semanas,
        mes_label=mes_label,
        anio=anio,
        mes=mes,
        entrenamientos_mes=entrenos_mes,
        hoy=hoy,
        resumen=resumen,   # <--- agregado
    )


# =========================
# API SIMPLIFICADA PARA PERFIL Y CALENDARIO
# =========================
@main_bp.post("/guardar_perfil")
def guardar_perfil():
    data = request.get_json()
    atleta = _find_atleta_by_id(data.get("id"))
    if atleta:
        for campo in ["edad", "altura", "peso", "telefono", "email"]:
            atleta[campo] = data.get(campo, atleta.get(campo))
        return jsonify({"status": "ok", "msg": "Perfil actualizado"})
    return jsonify({"status": "error", "msg": "Atleta no encontrado"}), 404


@main_bp.post("/nuevo_entrenamiento")
def nuevo_entrenamiento():
    data = request.get_json()
    atleta = _find_atleta_by_id(data.get("atleta_id"))
    if not atleta:
        return jsonify({"status": "error", "msg": "Atleta no encontrado"}), 404
    fecha_dt = datetime.strptime(data["fecha"], "%Y-%m-%d")
    _ENTRENAMIENTOS.append(
        _VMEntrenamiento(atleta["nombre"], fecha_dt, data["tipo"], data["detalle"])
    )
    return jsonify({"status": "ok"})


@main_bp.post("/editar_entrenamiento")
def editar_entrenamiento():
    data = request.get_json()
    for e in _ENTRENAMIENTOS:
        if e.id == data["id"]:
            e.tipo = data.get("tipo", e.tipo)
            e.detalle = data.get("detalle", e.detalle)
            return jsonify({"status": "ok"})
    return jsonify({"status": "error"}), 404


@main_bp.post("/bloquear_dia")
def bloquear_dia():
    data = request.get_json()
    atleta = _find_atleta_by_id(data.get("atleta_id"))
    if not atleta:
        return jsonify({"status": "error"}), 404
    fecha_dt = datetime.strptime(data["fecha"], "%Y-%m-%d")
    bloqueado = _VMEntrenamiento(atleta["nombre"], fecha_dt, "Bloqueado", "Día sin entrenamiento")
    bloqueado.bloqueado = True
    _ENTRENAMIENTOS.append(bloqueado)
    return jsonify({"status": "ok"})


@main_bp.get("/logout")
def logout():
    """Simula el cierre de sesión"""
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.dashboard_entrenador"))
