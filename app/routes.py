from datetime import datetime, timedelta, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, DiaPlan, Rutina
from app.extensions import db

main_bp = Blueprint("main", __name__)

# =======================
# 📅 Utilidades de fechas
# =======================
def start_of_week(d: date) -> date:
    return d - timedelta(days=(d.weekday() % 7))


def week_dates(center: date | None = None):
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]


# =======================
# 🔐 Login / Logout
# =======================
@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.email == "admin@vir.app":
            return redirect(url_for("main.dashboard_entrenador"))
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre} 👋", "success")
            if user.email == "admin@vir.app":
                return redirect(url_for("main.dashboard_entrenador"))
            return redirect(url_for("main.perfil_usuario", user_id=user.id))
        flash("❌ Usuario o contraseña incorrectos.", "danger")
    return render_template("login.html")


@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))


# =======================
# 👤 Perfiles
# =======================
@main_bp.route("/perfil")
@login_required
def perfil():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id):
    if current_user.email == "admin@vir.app":
        user = User.query.get_or_404(user_id)
    else:
        if current_user.id != user_id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for("main.perfil"))
        user = current_user

    fechas = week_dates()
    planes = {p.fecha: p for p in DiaPlan.query.filter(
        DiaPlan.user_id == user.id,
        DiaPlan.fecha.in_(fechas)
    ).all()}

    for f in fechas:
        if f not in planes:
            nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
            db.session.add(nuevo)
            planes[f] = nuevo
    db.session.commit()

    labels = [f.strftime("%d/%m") for f in fechas]
    propuesto = [planes[f].propuesto_score or 0 for f in fechas]
    realizado = [planes[f].realizado_score or 0 for f in fechas]

    try:
        rutinas = Rutina.query.order_by(Rutina.id.desc()).limit(20).all()
    except Exception:
        rutinas = []

    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

    return render_template(
        "perfil.html",
        user=user,
        fechas=fechas,
        planes=planes,
        labels=labels,
        propuesto=propuesto,
        realizado=realizado,
        rutinas=rutinas,
        semana_str=semana_str
    )


# =======================
# 💾 Guardar día de plan
# =======================
@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    user_id = int(request.form["user_id"])
    if current_user.email != "admin@vir.app" and current_user.id != user_id:
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    fecha_str = request.form["fecha"].strip()
    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        try:
            fecha = datetime.fromisoformat(fecha_str).date()
        except ValueError:
            flash("Fecha inválida.", "danger")
            return redirect(url_for("main.perfil_usuario", user_id=user_id))

    plan_type = request.form.get("plan_type", "descanso")
    warmup = request.form.get("warmup", "")
    main = request.form.get("main", "")
    finisher = request.form.get("finisher", "")
    propuesto = int(request.form.get("propuesto_score", "0") or 0)
    realizado = int(request.form.get("realizado_score", "0") or 0)

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = plan_type
    plan.warmup = warmup
    plan.main = main
    plan.finisher = finisher
    plan.propuesto_score = propuesto
    plan.realizado_score = realizado
    db.session.commit()

    flash("✅ Día actualizado.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))


# =======================
# 🧑‍🏫 Dashboard entrenador
# =======================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))
    atletas = User.query.filter(User.email != "admin@vir.app").all()
    return render_template("dashboard_entrenador.html", atletas=atletas)


# ===================================
# 👑 Crear usuario (solo admin)
# ===================================
@main_bp.route("/admin/create_user", methods=["POST"])
@login_required
def admin_create_user():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    nombre = request.form.get("nombre")
    email = request.form.get("email").lower().strip()
    grupo = request.form.get("grupo", "Atleta")
    password = request.form.get("password")

    if not (nombre and email and password):
        flash("Todos los campos son obligatorios.", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    if User.query.filter_by(email=email).first():
        flash("Ese correo ya existe.", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    nuevo = User(nombre=nombre, email=email, grupo=grupo)
    nuevo.set_password(password)
    db.session.add(nuevo)
    db.session.commit()
    flash(f"✅ Usuario {nombre} creado correctamente.", "success")
    return redirect(url_for("main.dashboard_entrenador"))


# ===================================
# ❌ Eliminar usuario (solo admin)
# ===================================
@main_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id):
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    user = User.query.get_or_404(user_id)
    if user.email == "admin@vir.app":
        flash("No podés eliminar al administrador.", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    planes = DiaPlan.query.filter_by(user_id=user.id).all()
    for p in planes:
        db.session.delete(p)

    db.session.delete(user)
    db.session.commit()

    flash(f"🗑️ Usuario {user.nombre} y sus planes fueron eliminados.", "info")
    return redirect(url_for("main.dashboard_entrenador"))


# ================================
# 📚 Listar rutinas (para perfil)
# ================================
@main_bp.route("/rutinas")
@login_required
def listar_rutinas():
    try:
        rutinas = Rutina.query.order_by(Rutina.id.desc()).all()
    except Exception:
        rutinas = []
    return render_template("rutinas.html", rutinas=rutinas)


# =====================================
# ➕ Crear rutina (solo admin)
# =====================================
@main_bp.route("/rutina/crear", methods=["POST"])
@login_required
def crear_rutina():
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    nombre = request.form.get("nombre")
    tipo = request.form.get("tipo")
    descripcion = request.form.get("descripcion")

    if not nombre:
        flash("El nombre es obligatorio.", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    nueva = Rutina(nombre=nombre, descripcion=descripcion, tipo=tipo, created_by=current_user.id)
    db.session.add(nueva)
    db.session.commit()
    flash(f"✅ Rutina '{nombre}' creada correctamente.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


# =====================================
# ➕ Agregar ejercicio a rutina
# =====================================
@main_bp.route("/rutina/<int:rutina_id>/add_ex", methods=["POST"])
@login_required
def agregar_ejercicio(rutina_id):
    if current_user.email != "admin@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    rutina = Rutina.query.get_or_404(rutina_id)
    nombre = request.form.get("nombre")
    series = request.form.get("series")
    reps = request.form.get("reps")
    descanso = request.form.get("descanso")
    imagen_url = request.form.get("imagen_url")
    nota = request.form.get("nota")

    if not nombre:
        flash("Debe tener nombre.", "danger")
        return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

    from app.models import RutinaItem
    item = RutinaItem(
        rutina_id=rutina.id,
        nombre=nombre,
        reps=reps,
        series=series,
        descanso=descanso,
        imagen_url=imagen_url,
        nota=nota
    )
    db.session.add(item)
    db.session.commit()
    flash(f"🏋️‍♂️ Ejercicio '{nombre}' agregado a {rutina.nombre}.", "success")
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


# ===========================================
# 🧰 Ruta temporal para crear el admin inicial
# ===========================================
@main_bp.route("/setup-admin")
def setup_admin():
    admin_email = "admin@vir.app"
    admin_pass = "V!ru_Admin-2025$X9"

    if User.query.filter_by(email=admin_email).first():
        return "✅ Admin ya existe. Entrá con admin@vir.app / V!ru_Admin-2025$X9"

    nuevo = User(nombre="Admin ViR", email=admin_email, grupo="Entrenador")
    nuevo.set_password(admin_pass)
    db.session.add(nuevo)
    db.session.commit()

    return f"✅ Admin creado correctamente.<br>Email: {admin_email}<br>Contraseña: {admin_pass}"
