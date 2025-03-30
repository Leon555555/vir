from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from app.models import db, Atleta, Entrenamiento, Coach
from datetime import datetime
import calendar

main = Blueprint('main', __name__)

@main.route('/')
def index():
    if 'coach_id' not in session:
        return redirect(url_for('main.login'))
    return redirect(url_for('main.dashboard'))

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        coach = Coach.query.filter_by(email=email).first()
        if coach and coach.check_password(password):
            session['coach_id'] = coach.id
            return redirect(url_for('main.dashboard'))
        else:
            flash('Credenciales incorrectas')
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.pop('coach_id', None)
    return redirect(url_for('main.login'))

@main.route('/dashboard')
def dashboard():
    if 'coach_id' not in session:
        return redirect(url_for('main.login'))

    atletas = Atleta.query.all()
    entrenamientos = Entrenamiento.query.all()
    hoy = datetime.today()
    year = hoy.year
    month = hoy.month
    semanas = calendar.Calendar().monthdayscalendar(year, month)

    atleta_seleccionado = request.args.get('atleta')
    return render_template(
        'dashboard.html',
        atletas=atletas,
        entrenamientos=entrenamientos,
        calendario_mensual=semanas,
        mes=month,
        anio=year,
        atleta_seleccionado=atleta_seleccionado
    )

@main.route('/nuevo_entrenamiento', methods=['POST'])
def nuevo_entrenamiento():
    if 'coach_id' not in session:
        return redirect(url_for('main.login'))

    nombre_atleta = request.form['atleta']
    atleta = Atleta.query.filter_by(nombre=nombre_atleta).first()
    if atleta:
        nuevo = Entrenamiento(
            atleta=atleta,
            fecha=datetime.strptime(request.form['fecha'], '%Y-%m-%d').date(),
            tipo=request.form['tipo'],
            detalle=request.form['detalle']
        )
        db.session.add(nuevo)
        db.session.commit()
        return redirect(url_for('main.dashboard', atleta=nombre_atleta))
    return "Atleta no encontrado", 404

@main.route('/borrar_entrenamiento/<int:id>', methods=['POST'])
def borrar_entrenamiento(id):
    if 'coach_id' not in session:
        return redirect(url_for('main.login'))

    entrenamiento = Entrenamiento.query.get(id)
    if entrenamiento:
        nombre = entrenamiento.atleta.nombre
        db.session.delete(entrenamiento)
        db.session.commit()
        return redirect(url_for('main.dashboard', atleta=nombre))
    return "Entrenamiento no encontrado", 404

@main.route('/perfil/<int:id>')
def perfil(id):
    if 'coach_id' not in session:
        return redirect(url_for('main.login'))

    atleta = Atleta.query.get_or_404(id)
    return render_template('perfil.html', atleta=atleta, hoy=datetime.today().date())

@main.route('/actualizar_tiempos/<int:id>', methods=['POST'])
def actualizar_tiempos(id):
    if 'coach_id' not in session:
        return redirect(url_for('main.login'))

    atleta = Atleta.query.get_or_404(id)
    atleta.pr_1000m = request.form.get('pr_1000m')
    atleta.pr_10k = request.form.get('pr_10k')
    atleta.pr_21k = request.form.get('pr_21k')
    atleta.pr_42k = request.form.get('pr_42k')
    db.session.commit()
    return redirect(url_for('main.perfil', id=id))
