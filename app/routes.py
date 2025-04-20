from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import db, Atleta
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

    entrenamientos_futuros = [e for e in atleta.entrenamientos if e.fecha >= hoy]
    entrenamientos_pasados = [e for e in atleta.entrenamientos if e.fecha < hoy]
    planificados_7dias = [e for e in atleta.entrenamientos if hoy <= e.fecha <= hoy + timedelta(days=7)]
    realizados_7dias = [e for e in atleta.entrenamientos if hace_7_dias <= e.fecha < hoy]

    total = len(planificados_7dias)
    realizados = len(realizados_7dias)
    progreso = int((realizados / total) * 100) if total else 0

    # Calendario mensual
    primer_dia = hoy.replace(day=1)
    _, dias_en_mes = calendar.monthrange(primer_dia.year, primer_dia.month)
    entrenamientos_del_mes = [
        e.fecha.day for e in atleta.entrenamientos
        if e.fecha.month == hoy.month and e.fecha.year == hoy.year
    ]

    calendario_mensual = []
    semana = []
    dia_actual = 1

    primer_dia_semana = primer_dia.weekday()
    for _ in range((primer_dia_semana + 1) % 7):
        semana.append(0)

    while dia_actual <= dias_en_mes:
        semana.append({
            "numero": dia_actual,
            "entreno": dia_actual in entrenamientos_del_mes
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
        entrenamientos_realizados=entrenamientos_pasados,
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
