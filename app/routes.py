from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from datetime import date, timedelta
from app.models import User, Sesion
from app.extensions import db

main_bp = Blueprint("main", __name__)

# ======================================
# INDEX Y LOGIN
# ======================================

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.email == "viru@vir.app":
            return redirect(url_for("main.dashboard_entrenador"))
        else:
            return redirect(url_for("main.perfil_usuario", user_id=current_user.id))
    return redirect(url_for("main.login"))


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Bienvenido {user.nombre} 👋", "success")
            if user.email == "viru@vir.app":
                return redirect(url_for("main.dashboard_entrenador"))
            else:
                return redirect(url_for("main.perfil_usuario", user_id=user.id))
        else:
            flash("❌ Usuario o contraseña incorrectos.", "danger")

    return render_template("login.html")


# ======================================
# REGISTRO DE NUEVO USUARIO
# ======================================

@main_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form.get("nombre")
        email = request.form.get("email")
        password = request.form.get("password")

        if not (nombre and email and password):
            flash("Por favor completa todos los campos", "danger")
            return redirect(url_for("main.register"))

        if User.query.filter_by(email=email).first():
            flash("Ese correo ya está registrado", "danger")
            return redirect(url_for("main.register"))

        nuevo = User(nombre=nombre, email=email)
        nuevo.set_password(password)
        db.session.add(nuevo)
        db.session.commit()

        flash("Cuenta creada correctamente. Ahora inicia sesión.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


# ======================================
# PERFIL UNIFICADO (ENTRENADOR O ATLETA)
# ======================================

@main_bp.route("/perfil")
@login_required
def perfil():
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))


@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id):
    if current_user.email == "viru@vir.app":
        user = User.query.get_or_404(user_id)
    else:
        if current_user.id != user_id:
            flash("Acceso denegado.", "danger")
            return redirect(url_for("main.perfil"))
        user = current_user

    # Traer todas las sesiones del atleta
    sesiones = Sesion.query.filter_by(user_id=user.id).order_by(Sesion.fecha.asc()).all()

    # Calcular última y próxima sesión
    hoy = date.today()
    ultima = None
    proxima = None
    for s in sesiones:
        if s.fecha <= hoy:
            ultima = s
        if s.fecha > hoy and proxima is None:
            proxima = s

    # Calcular semana actual (lunes-domingo)
    lunes = hoy - timedelta(days=hoy.weekday())
    semana = []
    sesiones_por_dia = {}
    for s in sesiones:
        sesiones_por_dia.setdefault(s.fecha, []).append(s)

    for i in range(7):
        d = lunes + timedelta(days=i)
        semana.append({
            "fecha": d,
            "hoy": (d == hoy),
            "tiene_sesion": d in sesiones_por_dia,
            "sesiones": sesiones_por_dia.get(d, [])
        })

    cumplimiento = round(100 * sum(1 for d in semana if d["tiene_sesion"]) / 7, 1)

    return render_template(
        "perfil.html",
        user=user,
        sesiones=sesiones,
        ultima=ultima,
        proxima=proxima,
        semana=semana,
        cumplimiento=cumplimiento
    )


# ======================================
# DASHBOARD DEL ENTRENADOR
# ======================================

@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atletas = User.query.filter(User.email != "viru@vir.app").all()
    return render_template("dashboard_entrenador.html", atletas=atletas)


# ======================================
# CREAR NUEVO ATLETA
# ======================================

@main_bp.route("/coach/nuevo", methods=["GET", "POST"])
@login_required
def nuevo_atleta():
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        email = request.form["email"]
        password = request.form["password"]
        grupo = request.form.get("grupo")
        calendario_url = request.form.get("calendario_url")

        atleta = User(
            nombre=nombre,
            email=email,
            grupo=grupo,
            calendario_url=calendario_url,
        )
        atleta.set_password(password)
        db.session.add(atleta)
        db.session.commit()

        flash(f"✅ Atleta '{nombre}' creado correctamente.", "success")
        return redirect(url_for("main.dashboard_entrenador"))

    return render_template("nuevo_atleta.html")


# ======================================
# EDITAR ATLETA
# ======================================

@main_bp.route("/coach/editar/<int:atleta_id>", methods=["GET", "POST"])
@login_required
def editar_atleta(atleta_id):
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atleta = User.query.get_or_404(atleta_id)

    if request.method == "POST":
        atleta.nombre = request.form["nombre"]
        atleta.email = request.form["email"]
        atleta.grupo = request.form.get("grupo")
        atleta.calendario_url = request.form.get("calendario_url")
        db.session.commit()
        flash("✅ Datos del atleta actualizados.", "success")
        return redirect(url_for("main.dashboard_entrenador"))

    return render_template("editar_atleta.html", atleta=atleta)


# ======================================
# ELIMINAR ATLETA
# ======================================

@main_bp.route("/coach/eliminar/<int:atleta_id>", methods=["POST"])
@login_required
def eliminar_atleta(atleta_id):
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atleta = User.query.get_or_404(atleta_id)
    db.session.delete(atleta)
    db.session.commit()
    flash(f"❌ Atleta '{atleta.nombre}' eliminado.", "warning")
    return redirect(url_for("main.dashboard_entrenador"))


# ======================================
# SESIONES DE ENTRENAMIENTO (ENTRENADOR)
# ======================================

@main_bp.route("/coach/sesiones/<int:atleta_id>", methods=["GET", "POST"])
@login_required
def sesiones_atleta(atleta_id):
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))

    atleta = User.query.get_or_404(atleta_id)

    if request.method == "POST":
        tipo = request.form.get("tipo")
        descripcion = request.form.get("descripcion")
        fecha = request.form.get("fecha")
        duracion = request.form.get("duracion")
        intensidad = request.form.get("intensidad")

        if not tipo or not fecha:
            flash("Completa los campos obligatorios.", "danger")
        else:
            nueva = Sesion(
                user_id=atleta.id,
                tipo=tipo,
                descripcion=descripcion,
                fecha=fecha,
                duracion=int(duracion or 0),
                intensidad=intensidad,
            )
            db.session.add(nueva)
            db.session.commit()
            flash("✅ Sesión agregada correctamente.", "success")

        return redirect(url_for("main.sesiones_atleta", atleta_id=atleta.id))

    sesiones = Sesion.query.filter_by(user_id=atleta.id).order_by(Sesion.fecha.desc()).all()
    return render_template("sesiones_atleta.html", atleta=atleta, sesiones=sesiones)


@main_bp.route("/coach/sesiones/eliminar/<int:sesion_id>", methods=["POST"])
@login_required
def eliminar_sesion(sesion_id):
    sesion = Sesion.query.get_or_404(sesion_id)
    if current_user.email != "viru@vir.app":
        flash("Acceso denegado.", "danger")
        return redirect(url_for("main.perfil"))
    db.session.delete(sesion)
    db.session.commit()
    flash("❌ Sesión eliminada.", "warning")
    return redirect(url_for("main.sesiones_atleta", atleta_id=sesion.user_id))


# ======================================
# LOGOUT
# ======================================

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("main.login"))
