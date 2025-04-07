from flask import Blueprint, render_template, request, redirect, url_for, session
from app.models import db, Atleta, Entrenamiento
from datetime import datetime, date, timedelta
import calendar

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

    return render_template(
        "perfil.html",
        atleta=atleta,
        hoy=hoy,
        entrenamientos_futuros=entrenamientos_futuros,
        entrenamientos_pasados=entrenamientos_pasados,
        progreso_semana=progreso
    )

# ACTUALIZAR MARCAS
@main.route('/actualizar_tiempos/<int:id>', methods=['POST'])
def actualizar_tiempos(id):
    atleta = Atleta.query.get_or_404(id)
    atleta.pr_1000m = request.form.get('pr_1000m')
    atleta.pr_10k = request.form.get('pr_10k')
    atleta.pr_21k = request.form.get('pr_21k')
    atleta.pr_42k = request.form.get('pr_42k')
    db.session.commit()
    return redirect(url_for('main.perfil', id=id))

# RUTA TEMPORAL PARA CREAR ATLETAS
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
