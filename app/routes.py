from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models import db, Atleta, Entrenamiento
from datetime import date, timedelta
import calendar

main_bp = Blueprint('main', __name__)

@main_bp.route("/")
def index():
    return redirect(url_for('main.login'))

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        atleta = Atleta.query.filter_by(email=email).first()
        if atleta and password == "1234":
            session["usuario_id"] = atleta.id
            return redirect(url_for("main.perfil", id=atleta.id))
        else:
            error = "Credenciales inválidas"
    return render_template("login.html", error=error)

@main_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))

@main_bp.route("/perfil/<int:id>")
def perfil(id):
    atleta = Atleta.query.get_or_404(id)
    hoy = date.today()
    hace_7_dias = hoy - timedelta(days=7)

    entrenamientos_futuros = [e for e in atleta.entrenamientos if e.fecha >= hoy and not e.realizado]
    entrenamientos_realizados = [e for e in atleta.entrenamientos if e.realizado]
    planificados_7dias = [e for e in atleta.entrenamientos if hoy <= e.fecha <= hoy + timedelta(days=7)]
    realizados_7dias = [e for e in atleta.entrenamientos if e.realizado and hace_7_dias <= e.fecha <= hoy]

    total = len(planificados_7dias)
    realizados = len(realizados_7dias)
    progreso = int((realizados / total) * 100) if total else 0

    # Íconos por tipo de entrenamiento
    iconos_por_tipo = {
        "carrera": "🏃",
        "bicicleta": "🚴",
        "natación": "🏊‍♂️",
        "fuerza": "💪",
        "descanso": "😴",
        "series pista": "🏟️",
        "estiramientos": "🤸"
    }

    # Calendario mensual
    primer_dia = hoy.replace(day=1)
    _, dias_en_mes = calendar.monthrange(primer_dia.year, primer_dia.month)
    entrenamientos_mes = [
        e for e in atleta.entrenamientos
        if e.fecha.month == hoy.month and e.fecha.year == hoy.year
    ]

    dias_entreno = {}
    for e in entrenamientos_mes:
        dia = e.fecha.day
        dias_entreno.setdefault(dia, []).append(iconos_por_tipo.get(e.tipo.lower(), "🏃"))

    calendario_mensual = []
    semana = []
    dia_actual = 1
    primer_dia_semana = primer_dia.weekday()

    for _ in range((primer_dia_semana + 1) % 7):
        semana.append(0)

    while dia_actual <= dias_en_mes:
        semana.append({
            "numero": dia_actual,
            "iconos": dias_entreno.get(dia_actual, [])
        })
        if len(semana) == 7:
            calendario_mensual.append(semana)
            semana = []
        dia_actual += 1

    if semana:
        while len(semana) < 7:
            semana.append(0)
        calendario_mensual.append(semana)

    return render_template(
        "perfil.html",
        atleta=atleta,
        hoy=hoy,
        entrenamientos_planificados=entrenamientos_futuros,
        entrenamientos_realizados=entrenamientos_realizados,
        progreso_semana=progreso,
        calendario_mensual=calendario_mensual
    )

@main_bp.route("/editar_perfil/<int:atleta_id>", methods=["POST"])
def editar_perfil(atleta_id):
    atleta = Atleta.query.get_or_404(atleta_id)
    atleta.nombre = request.form["nombre"]
    atleta.apellido = request.form["apellido"]
    atleta.correo = request.form["correo"]
    db.session.commit()
    flash("✅ Perfil actualizado correctamente.", "success")
    return redirect(url_for("main.perfil", id=atleta.id))

@main_bp.route("/entrena-en-casa")
def entrena_en_casa():
    ejercicios = [
        {"nombre": "Flexiones", "video": "flexiones.mp4"},
        {"nombre": "Sentadillas", "video": "sentadillas.mp4"},
    ]
    return render_template("entrena_en_casa.html", ejercicios=ejercicios)

@main_bp.route("/dashboard")
def dashboard():
    atletas = Atleta.query.all()
    atleta_seleccionado = request.args.get("atleta")
    entrenamientos = Entrenamiento.query.all()
    hoy = date.today()
    anio = hoy.year
    mes = hoy.month
    primer_dia = date(anio, mes, 1)
    _, dias_en_mes = calendar.monthrange(anio, mes)

    calendario_mensual = []
    semana = []
    dia_actual = 1
    primer_dia_semana = primer_dia.weekday()
    for _ in range((primer_dia_semana + 1) % 7):
        semana.append(0)

    while dia_actual <= dias_en_mes:
        semana.append(dia_actual)
        if len(semana) == 7:
            calendario_mensual.append(semana)
            semana = []
        dia_actual += 1

    if semana:
        while len(semana) < 7:
            semana.append(0)
        calendario_mensual.append(semana)

    return render_template(
        "dashboard.html",
        atletas=atletas,
        atleta_seleccionado=atleta_seleccionado,
        calendario_mensual=calendario_mensual,
        entrenamientos=entrenamientos,
        mes=mes,
        anio=anio
    )

@main_bp.route("/nuevo_entrenamiento", methods=["POST"])
def nuevo_entrenamiento():
    atleta_nombre = request.form["atleta"]
    fecha = request.form["fecha"]
    tipo = request.form["tipo"]
    detalle = request.form["detalle"]

    atleta = Atleta.query.filter_by(nombre=atleta_nombre).first()
    if not atleta:
        flash("❌ Atleta no encontrado", "danger")
        return redirect(url_for("main.dashboard"))

    nuevo = Entrenamiento(
        atleta_id=atleta.id,
        fecha=fecha,
        tipo=tipo,
        detalle=detalle,
        realizado=False
    )
    db.session.add(nuevo)
    db.session.commit()

    flash("✅ Entrenamiento guardado correctamente", "success")
    return redirect(url_for("main.dashboard", atleta=atleta.nombre))

@main_bp.route("/marcar_realizado_ajax", methods=["POST"])
def marcar_realizado_ajax():
    data = request.get_json()
    entrenamiento_id = data.get("id")
    entrenamiento = Entrenamiento.query.get(entrenamiento_id)

    if not entrenamiento:
        return jsonify({"success": False, "message": "No encontrado"}), 404

    entrenamiento.realizado = True
    db.session.commit()

    return jsonify({"success": True})
