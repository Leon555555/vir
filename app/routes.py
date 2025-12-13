from __future__ import annotations

from datetime import datetime, timedelta, date
from calendar import monthrange
from typing import Any, Dict, List, Tuple

from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, jsonify, current_app
)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import text
from werkzeug.utils import secure_filename
import os

from app.models import (
    User, DiaPlan, Rutina, Ejercicio, RutinaItem,
    AthleteCheck, AthleteDayResult
)
from app.extensions import db

main_bp = Blueprint("main", __name__)

# =============================================================
# FECHAS / UTILIDADES
# =============================================================
def start_of_week(d: date) -> date:
    return d - timedelta(days=d.weekday())

def week_dates(center: date | None = None) -> List[date]:
    base = center or date.today()
    start = start_of_week(base)
    return [start + timedelta(days=i) for i in range(7)]

def month_dates(year: int, month: int) -> List[date]:
    _, last = monthrange(year, month)
    return [date(year, month, d) for d in range(1, last + 1)]

def safe_parse_ymd(s: str, fallback: date | None = None) -> date:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.fromisoformat(s).date()
        except Exception:
            return fallback or date.today()

def is_admin() -> bool:
    return bool(current_user.is_authenticated and current_user.email == "admin@vir.app")

# =============================================================
# SERIALIZADORES
# =============================================================
def serialize_user(u: User) -> Dict[str, Any]:
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "grupo": u.grupo or ""}

def serialize_rutina(r: Rutina) -> Dict[str, Any]:
    return {"id": r.id, "nombre": r.nombre, "tipo": r.tipo, "descripcion": r.descripcion, "created_by": r.created_by}

# =============================================================
# HOME / LOGIN
# =============================================================
@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        if is_admin():
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
            flash(f"Bienvenido {user.nombre}", "success")
            if is_admin():
                return redirect(url_for("main.dashboard_entrenador"))
            return redirect(url_for("main.perfil_usuario", user_id=user.id))
        flash("Datos incorrectos", "danger")
    return render_template("login.html")

@main_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada", "info")
    return redirect(url_for("main.login"))

@main_bp.route("/perfil")
@login_required
def perfil_redirect():
    if is_admin():
        return redirect(url_for("main.dashboard_entrenador"))
    return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

# =============================================================
# PERFIL (ATLETA)
# =============================================================
@main_bp.route("/perfil/<int:user_id>")
@login_required
def perfil_usuario(user_id: int):
    try:
        user = User.query.get_or_404(user_id)

        # Seguridad: atleta no ve otro perfil
        if not is_admin() and current_user.id != user.id:
            flash("Acceso denegado", "danger")
            return redirect(url_for("main.perfil_usuario", user_id=current_user.id))

        center = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())
        fechas = week_dates(center)

        # planes semana
        planes_db = DiaPlan.query.filter(DiaPlan.user_id == user.id, DiaPlan.fecha.in_(fechas)).all()
        planes: Dict[date, DiaPlan] = {p.fecha: p for p in planes_db}

        # crear vacíos si faltan
        for f in fechas:
            if f not in planes:
                nuevo = DiaPlan(user_id=user.id, fecha=f, plan_type="descanso")
                planes[f] = nuevo
                db.session.add(nuevo)
        db.session.commit()

        # mes
        hoy = date.today()
        dias_mes = month_dates(hoy.year, hoy.month)
        planes_mes = {
            p.fecha: p
            for p in DiaPlan.query.filter(DiaPlan.user_id == user.id, DiaPlan.fecha.in_(dias_mes)).all()
        }

        semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"

        # rutinas para tab
        rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

        # rutina_by_day + items_by_day
        rutina_by_day: Dict[date, Rutina | None] = {}
        items_by_day: Dict[date, List[RutinaItem]] = {}
        rutina_items_cache: Dict[int, List[RutinaItem]] = {}

        for f in fechas:
            plan = planes[f]
            rutina = None
            items: List[RutinaItem] = []

            if plan.main and isinstance(plan.main, str) and plan.main.startswith("RUTINA:"):
                rid_str = plan.main.split(":", 1)[1].strip()
                if rid_str.isdigit():
                    rid = int(rid_str)
                    rutina = Rutina.query.get(rid)
                    if rid in rutina_items_cache:
                        items = rutina_items_cache[rid]
                    else:
                        items = (
                            RutinaItem.query.filter_by(rutina_id=rid)
                            .order_by(RutinaItem.id.asc())
                            .all()
                        )
                        rutina_items_cache[rid] = items

            rutina_by_day[f] = rutina
            items_by_day[f] = items

        # done_set de checks por ejercicio
        done_set: set[Tuple[date, int]] = set()
        try:
            checks = AthleteCheck.query.filter(
                AthleteCheck.user_id == user.id,
                AthleteCheck.fecha.in_(fechas)
            ).all()
            for c in checks:
                if c.done:
                    done_set.add((c.fecha, c.rutina_item_id))
        except Exception:
            done_set = set()

        # ✅ resultados diarios (lo realizado) sin tocar lo propuesto
        result_by_day: Dict[date, AthleteDayResult] = {}
        try:
            res = AthleteDayResult.query.filter(
                AthleteDayResult.user_id == user.id,
                AthleteDayResult.fecha.in_(fechas)
            ).all()
            result_by_day = {r.fecha: r for r in res}
        except Exception:
            result_by_day = {}

        return render_template(
            "perfil.html",
            user=user,
            fechas=fechas,
            planes=planes,
            hoy=hoy,
            dias_mes=dias_mes,
            planes_mes=planes_mes,
            semana_str=semana_str,
            rutinas=rutinas,

            rutina_by_day=rutina_by_day,
            items_by_day=items_by_day,
            done_set=done_set,

            # ✅ lo realizado
            result_by_day=result_by_day,

            center=center,
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Error cargando perfil: {e}", "danger")
        return redirect(url_for("main.index"))

# =============================================================
# ✅ CHECK por ejercicio (JSON)
# =============================================================
@main_bp.route("/athlete/check_item", methods=["POST"])
@login_required
def athlete_check_item():
    """
    JSON:
      { "fecha":"YYYY-MM-DD", "item_id":123, "done": true/false }
    """
    try:
        payload = request.get_json(silent=True) or {}
        fecha = safe_parse_ymd(payload.get("fecha", ""), fallback=date.today())
        item_id = int(payload.get("item_id"))
        done = bool(payload.get("done", True))

        item = RutinaItem.query.get_or_404(item_id)

        existing = AthleteCheck.query.filter_by(
            user_id=current_user.id, fecha=fecha, rutina_item_id=item.id
        ).first()

        if existing:
            existing.done = done
            existing.updated_at = datetime.utcnow()
        else:
            db.session.add(AthleteCheck(
                user_id=current_user.id,
                fecha=fecha,
                rutina_item_id=item.id,
                done=done,
                updated_at=datetime.utcnow(),
            ))

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

# =============================================================
# ✅ GUARDAR "LO REALIZADO" (sin tocar lo propuesto)
# =============================================================
@main_bp.route("/athlete/day_result", methods=["POST"])
@login_required
def athlete_day_result():
    """
    JSON:
    {
      "fecha":"YYYY-MM-DD",
      "did_workout": true/false,
      "warmup_done":"...",
      "main_done":"...",
      "finisher_done":"...",
      "notes":"..."
    }
    """
    try:
        payload = request.get_json(silent=True) or {}
        fecha = safe_parse_ymd(payload.get("fecha", ""), fallback=date.today())

        did_workout = bool(payload.get("did_workout", False))
        warmup_done = (payload.get("warmup_done") or "").strip()
        main_done = (payload.get("main_done") or "").strip()
        finisher_done = (payload.get("finisher_done") or "").strip()
        notes = (payload.get("notes") or "").strip()

        existing = AthleteDayResult.query.filter_by(
            user_id=current_user.id, fecha=fecha
        ).first()

        if existing:
            existing.did_workout = did_workout
            existing.warmup_done = warmup_done
            existing.main_done = main_done
            existing.finisher_done = finisher_done
            existing.notes = notes
            existing.updated_at = datetime.utcnow()
        else:
            db.session.add(AthleteDayResult(
                user_id=current_user.id,
                fecha=fecha,
                did_workout=did_workout,
                warmup_done=warmup_done,
                main_done=main_done,
                finisher_done=finisher_done,
                notes=notes,
                updated_at=datetime.utcnow(),
            ))

        db.session.commit()
        return jsonify({"ok": True})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

# =============================================================
# ✅ BLOQUEAR DÍA "NO PUEDO ENTRENAR" (desde Calendario)
#   guardamos en DiaPlan.puede_entrenar = "No" / "Si"
# =============================================================
@main_bp.route("/athlete/toggle_can_train", methods=["POST"])
@login_required
def athlete_toggle_can_train():
    """
    JSON: { "fecha":"YYYY-MM-DD", "can_train": true/false }
    """
    try:
        payload = request.get_json(silent=True) or {}
        fecha = safe_parse_ymd(payload.get("fecha", ""), fallback=date.today())
        can_train = bool(payload.get("can_train", True))

        plan = DiaPlan.query.filter_by(user_id=current_user.id, fecha=fecha).first()
        if not plan:
            plan = DiaPlan(user_id=current_user.id, fecha=fecha, plan_type="descanso")
            db.session.add(plan)

        plan.puede_entrenar = "Si" if can_train else "No"
        db.session.commit()
        return jsonify({"ok": True, "puede_entrenar": plan.puede_entrenar})

    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(e)}), 500

# =============================================================
# ADMIN: GUARDAR ENTRENAMIENTO DEL DÍA (coach)
# =============================================================
@main_bp.route("/dia/save", methods=["POST"])
@login_required
def save_day():
    if not is_admin():
        flash("Solo el admin puede editar entrenamientos", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user_id = int(request.form["user_id"])
    fecha = safe_parse_ymd(request.form["fecha"])

    plan = DiaPlan.query.filter_by(user_id=user_id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=user_id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = request.form.get("plan_type", "descanso")
    plan.warmup = request.form.get("warmup", "")
    plan.main = request.form.get("main", "")
    plan.finisher = request.form.get("finisher", "")
    plan.propuesto_score = int(request.form.get("propuesto_score", 0))

    db.session.commit()
    flash("Entrenamiento actualizado", "success")
    return redirect(url_for("main.perfil_usuario", user_id=user_id))

# =============================================================
# DASHBOARD ENTRENADOR
# =============================================================
@main_bp.route("/coach/dashboard")
@login_required
def dashboard_entrenador():
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    atletas_db = User.query.filter(User.email != "admin@vir.app").all()
    rutinas_db = Rutina.query.order_by(Rutina.id.desc()).all()
    ejercicios_db = Ejercicio.query.order_by(Ejercicio.nombre).all()

    atletas = [serialize_user(a) for a in atletas_db]
    rutinas = [serialize_rutina(r) for r in rutinas_db]
    hoy = date.today()

    return render_template(
        "dashboard_entrenador.html",
        atletas=atletas,
        rutinas=rutinas,
        ejercicios=ejercicios_db,
        hoy=hoy
    )

# =============================================================
# CRUD USUARIOS
# =============================================================
@main_bp.route("/admin/delete_user/<int:user_id>", methods=["POST"])
@login_required
def admin_delete_user(user_id: int):
    if not is_admin():
        flash("Acceso denegado", "danger")
        return redirect(url_for("main.perfil_redirect"))

    user = User.query.get_or_404(user_id)
    if user.email == "admin@vir.app":
        flash("No se puede eliminar admin", "warning")
        return redirect(url_for("main.dashboard_entrenador"))

    DiaPlan.query.filter_by(user_id=user.id).delete()
    AthleteDayResult.query.filter_by(user_id=user.id).delete()
    AthleteCheck.query.filter_by(user_id=user.id).delete()

    db.session.delete(user)
    db.session.commit()

    flash("Atleta eliminado", "success")
    return redirect(url_for("main.dashboard_entrenador"))

# =============================================================
# CREAR RUTINA
# =============================================================
@main_bp.route("/crear_rutina", methods=["POST"])
@login_required
def crear_rutina():
    if not is_admin():
        flash("Solo el admin puede crear rutinas", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = request.form.get("nombre", "").strip()
    tipo = request.form.get("tipo", "").strip()
    descripcion = request.form.get("descripcion", "").strip()

    if not nombre:
        flash("El nombre es obligatorio", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nueva = Rutina(nombre=nombre, tipo=tipo, descripcion=descripcion, created_by=current_user.id)
    db.session.add(nueva)
    db.session.commit()

    flash("Rutina creada correctamente", "success")
    return redirect(url_for("main.dashboard_entrenador"))

# =============================================================
# CREAR EJERCICIO DEL BANCO (CON VIDEO)
#   - guarda en static/videos/
# =============================================================
@main_bp.route("/admin/ejercicios/nuevo", methods=["POST"])
@login_required
def admin_nuevo_ejercicio():
    if not is_admin():
        flash("Solo el admin puede crear ejercicios", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    nombre = request.form.get("nombre", "").strip()
    categoria = request.form.get("categoria", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    file = request.files.get("video")

    if not nombre or not file:
        flash("Falta el nombre o el vídeo del ejercicio", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    filename = secure_filename(file.filename)
    if not filename:
        flash("Nombre de archivo no válido", "danger")
        return redirect(url_for("main.dashboard_entrenador"))

    upload_folder = os.path.join(current_app.static_folder, "videos")
    os.makedirs(upload_folder, exist_ok=True)

    save_path = os.path.join(upload_folder, filename)
    file.save(save_path)

    ejercicio = Ejercicio(nombre=nombre, categoria=categoria, descripcion=descripcion, video_filename=filename)
    db.session.add(ejercicio)
    db.session.commit()

    flash("Ejercicio subido al banco correctamente", "success")
    return redirect(url_for("main.dashboard_entrenador"))

# =============================================================
# CONSTRUCTOR DE RUTINA
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/builder")
@login_required
def rutina_builder(rutina_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    items = RutinaItem.query.filter_by(rutina_id=rutina.id).order_by(RutinaItem.id).all()
    ejercicios = Ejercicio.query.order_by(Ejercicio.nombre).all()

    return render_template("rutina_builder.html", rutina=rutina, items=items, ejercicios=ejercicios)

# =============================================================
# AÑADIR EJERCICIO A RUTINA
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/add_item", methods=["POST"])
@login_required
def rutina_add_item(rutina_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    rutina = Rutina.query.get_or_404(rutina_id)
    ejercicio_id = request.form.get("ejercicio_id", type=int)

    if not ejercicio_id:
        flash("Falta el ejercicio a añadir", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

    ejercicio = Ejercicio.query.get_or_404(ejercicio_id)

    series = request.form.get("series", "").strip()
    reps = request.form.get("reps", "").strip()
    descanso = request.form.get("descanso", "").strip()

    item = RutinaItem(
        rutina_id=rutina.id,
        ejercicio_id=ejercicio.id,
        nombre=ejercicio.nombre,
        series=series,
        reps=reps,
        descanso=descanso,
        # ✅ consistente con tu modelo / tu layout
        video_url=f"videos/{ejercicio.video_filename}",
    )

    db.session.add(item)
    db.session.commit()

    flash("Ejercicio añadido a la rutina", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina.id))

# =============================================================
# ACTUALIZAR ITEM
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/update", methods=["POST"])
@login_required
def rutina_update_item(rutina_id: int, item_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    if item.rutina_id != rutina_id:
        flash("Item inválido", "danger")
        return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

    item.series = request.form.get("series", "").strip()
    item.reps = request.form.get("reps", "").strip()
    item.descanso = request.form.get("descanso", "").strip()
    # ✅ tu modelo es nota
    item.nota = request.form.get("nota", "").strip()

    db.session.commit()
    flash("Cambios guardados", "success")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

# =============================================================
# ELIMINAR ITEM
# =============================================================
@main_bp.route("/rutinas/<int:rutina_id>/items/<int:item_id>/delete", methods=["POST"])
@login_required
def rutina_delete_item(rutina_id: int, item_id: int):
    if not is_admin():
        flash("Solo el admin puede editar rutinas", "danger")
        return redirect(url_for("main.perfil_redirect"))

    item = RutinaItem.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()

    flash("Ejercicio eliminado de la rutina", "info")
    return redirect(url_for("main.rutina_builder", rutina_id=rutina_id))

# =============================================================
# PLANIFICADOR (COACH)
# =============================================================
@main_bp.route("/coach/planificador/<int:user_id>")
@login_required
def coach_planificador(user_id: int):
    if not is_admin():
        return "Acceso denegado", 403

    atleta = User.query.get_or_404(user_id)
    center_date = safe_parse_ymd(request.args.get("center", ""), fallback=date.today())
    fechas = week_dates(center_date)

    planes_db = DiaPlan.query.filter(DiaPlan.user_id == atleta.id, DiaPlan.fecha.in_(fechas)).all()
    planes = {p.fecha: p for p in planes_db}

    for f in fechas:
        if f not in planes:
            nuevo = DiaPlan(user_id=atleta.id, fecha=f, plan_type="descanso")
            planes[f] = nuevo
            db.session.add(nuevo)
    db.session.commit()

    semana_str = f"{fechas[0].strftime('%d/%m')} - {fechas[-1].strftime('%d/%m')}"
    rutinas = Rutina.query.order_by(Rutina.id.desc()).all()

    return render_template(
        "coach/planificador.html",
        atleta=atleta,
        fechas=fechas,
        planes=planes,
        rutinas=rutinas,
        semana_str=semana_str,
        center=center_date
    )

@main_bp.route("/coach/planificador/<int:user_id>/guardar_dia", methods=["POST"])
@login_required
def coach_guardar_dia(user_id: int):
    if not is_admin():
        return "Acceso denegado", 403

    atleta = User.query.get_or_404(user_id)
    fecha = safe_parse_ymd(request.form.get("fecha", ""), fallback=date.today())
    center = safe_parse_ymd(request.form.get("center", ""), fallback=fecha)

    plan = DiaPlan.query.filter_by(user_id=atleta.id, fecha=fecha).first()
    if not plan:
        plan = DiaPlan(user_id=atleta.id, fecha=fecha)
        db.session.add(plan)

    plan.plan_type = request.form.get("plan_type", "descanso")
    plan.warmup = request.form.get("warmup", "")
    plan.finisher = request.form.get("finisher", "")
    plan.propuesto_score = int(request.form.get("propuesto_score", 0))

    rutina_id = request.form.get("rutina_id", type=int)
    if rutina_id:
        plan.main = f"RUTINA:{rutina_id}"
    else:
        plan.main = request.form.get("main", "")

    db.session.commit()
    flash("Día guardado ✔", "success")
    return redirect(url_for("main.coach_planificador", user_id=atleta.id, center=center.isoformat()))

@main_bp.route("/coach/planificador/<int:user_id>/copiar_semana", methods=["POST"])
@login_required
def coach_copiar_semana(user_id: int):
    if not is_admin():
        return "Acceso denegado", 403

    atleta = User.query.get_or_404(user_id)
    center = safe_parse_ymd(request.form.get("center", ""), fallback=date.today())

    semana_origen = week_dates(center)
    semana_destino = [d + timedelta(days=7) for d in semana_origen]

    planes_origen = {
        p.fecha: p
        for p in DiaPlan.query.filter(DiaPlan.user_id == atleta.id, DiaPlan.fecha.in_(semana_origen)).all()
    }

    for f_o, f_d in zip(semana_origen, semana_destino):
        plan_o = planes_origen.get(f_o)
        if not plan_o:
            continue

        plan_d = DiaPlan.query.filter_by(user_id=atleta.id, fecha=f_d).first()
        if not plan_d:
            plan_d = DiaPlan(user_id=atleta.id, fecha=f_d)
            db.session.add(plan_d)

        plan_d.plan_type = plan_o.plan_type
        plan_d.warmup = plan_o.warmup
        plan_d.main = plan_o.main
        plan_d.finisher = plan_o.finisher
        plan_d.propuesto_score = plan_o.propuesto_score

        plan_d.realizado_score = 0
        plan_d.puede_entrenar = None
        plan_d.dificultad = None
        plan_d.comentario_atleta = None

    db.session.commit()
    flash("Semana copiada correctamente ✔", "success")
    return redirect(url_for("main.coach_planificador", user_id=atleta.id, center=(center + timedelta(days=7)).isoformat()))

# =============================================================
# FIX TABLAS EN RENDER (una vez)
# =============================================================
@main_bp.route("/fix-athlete-check-table")
@login_required
def fix_athlete_check_table():
    if not is_admin():
        return "Acceso denegado", 403

    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS athlete_check (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                rutina_item_id INTEGER NOT NULL REFERENCES rutina_item(id) ON DELETE CASCADE,
                done BOOLEAN NOT NULL DEFAULT TRUE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, fecha, rutina_item_id)
            );
        """))
        db.session.commit()
        return "TABLA athlete_check OK ✔", 200
    except Exception as e:
        db.session.rollback()
        return f"ERROR creando athlete_check: {e}", 500

@main_bp.route("/fix-athlete-day-result-table")
@login_required
def fix_athlete_day_result_table():
    if not is_admin():
        return "Acceso denegado", 403

    try:
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS athlete_day_result (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                fecha DATE NOT NULL,
                did_workout BOOLEAN NOT NULL DEFAULT FALSE,
                warmup_done TEXT,
                main_done TEXT,
                finisher_done TEXT,
                notes TEXT,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE(user_id, fecha)
            );
        """))
        db.session.commit()
        return "TABLA athlete_day_result OK ✔", 200
    except Exception as e:
        db.session.rollback()
        return f"ERROR creando athlete_day_result: {e}", 500

# =============================================================
# HEALTHCHECK
# =============================================================
@main_bp.route("/healthz")
def healthz():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()})
