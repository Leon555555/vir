from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import db, Atleta
from datetime import date, timedelta
import calendar  # <-- Import necesario para el calendario mensual

main = Blueprint('main', __name__)

# LOGIN
@main.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        atleta = Atleta.query.filter_by(email=email).first()
        if atleta and password == "1234":  # Contraseña fija por ahora
            session["usuario_id"] = atleta.id
            return redirect(url_for("main.perfil", id=atleta.id))
        else:
            error = "Credenciales inválidas"
    return render_template("login.html", error=error)

# LOGOUT
@main.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login"))

# HOME
@main.route('/')
def index():
    return redirect(url_for('main.login'))

# PERFIL DEL ATLETA
@main.route("/perfil/<int:id>")
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

    # Generar calendario mensual del mes actual
    primer_dia = hoy.replace(day=1)
    _, dias_en_mes = calendar.monthrange(primer_dia.year, primer_dia.month)
    calendario_mensual = []
    semana = []
    dia_actual = 1

    # Añadir días en blanco al inicio
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
        "perfil.html",
        atleta=atleta,
        hoy=hoy,
        entrenamientos_planificados=entrenamientos_futuros,
        entrenamientos_realizados=entrenamientos_pasados,
        progreso_semana=progreso,
        calendario_mensual=calendario_mensual
    )

# FORMULARIO PARA EDITAR PERFIL Y MARCAS
@main.route('/perfil/editar/<int:id>', methods=['GET', 'POST'])
def editar_perfil(id):
    atleta = Atleta.query.get_or_404(id)

    if request.method == 'POST':
        atleta.email = request.form['email']
        atleta.telefono = request.form['telefono']
        atleta.edad = request.form['edad']
        atleta.altura = request.form['altura']
        atleta.peso = request.form['peso']
        atleta.pr_1000 = request.form['pr_1000']
        atleta.pr_10k = request.form['pr_10k']
        atleta.pr_21k = request.form['pr_21k']
        atleta.pr_42k = request.form['pr_42k']

        db.session.commit()
        return redirect(url_for('main.perfil', id=atleta.id))

    return render_template("editar_perfil.html", atleta=atleta)

# RUTA TEMPORAL PARA CREAR ATLETAS DE PRUEBA
@main.route("/crear_atletas")
def crear_atletas():
    nombres = [
        "Leandro Videla",
        "Lucas Alonso Duró",
        "Guillaume Dubos",
        "Federico Civitillo",
        "Davis Sivilla",
        "Jordi Marti",
        "Guido Mure"
    ]
    for nombre in nombres:
        email = nombre.lower().replace(" ", "_").replace("ó", "o") + "@gmail.com"
        if not Atleta.query.filter_by(nombre=nombre).first():
            nuevo = Atleta(nombre=nombre, email=email)
            db.session.add(nuevo)
    db.session.commit()
    return "Atletas creados correctamente."
