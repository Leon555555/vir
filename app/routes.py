from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///atletas.db'
db = SQLAlchemy(app)

class Atleta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    edad = db.Column(db.Integer)
    email = db.Column(db.String(100))
    # Agrega otros campos necesarios

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        # Lógica de autenticación
        return redirect(url_for('perfil', atleta_id=1))  # Redirige al perfil del atleta con ID 1
    return render_template('login.html', error=error)

@app.route('/perfil/<int:atleta_id>', methods=['GET', 'POST'])
def perfil(atleta_id):
    atleta = Atleta.query.get_or_404(atleta_id)
    if request.method == 'POST':
        # Actualiza los datos del atleta con los valores del formulario
        atleta.nombre = request.form['nombre']
        atleta.edad = request.form['edad']
        atleta.email = request.form['email']
        # Actualiza otros campos según sea necesario
        db.session.commit()
        flash('Perfil actualizado exitosamente.')
        return redirect(url_for('perfil', atleta_id=atleta.id))
    return render_template('perfil.html', atleta=atleta)

if __name__ == '__main__':
    app.run(debug=True)
