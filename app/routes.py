from flask import Blueprint, render_template, jsonify, request
from datetime import datetime
import calendar

main = Blueprint("main", __name__)

# Simulación de base de datos
DIAS_CALENDARIO = {}  # Estructura: { '2025-04-24': {'tipo': 'run', 'comentario': 'Día clave', 'bloqueado': True} }

# Simulación de entrenamientos por atleta
ENTRENAMIENTOS = {
    1: {
        'planificados': [
            {'id': 1, 'fecha': datetime(2025, 4, 24), 'detalle': 'Fondo largo', 'tipo': 'run'},
        ],
        'realizados': [
            {'id': 2, 'fecha': datetime(2025, 4, 20), 'detalle': 'Series', 'tipo': 'series'}
        ]
    }
}

ATLETAS = {
    1: {
        'nombre': 'Leandro Videla',
        'correo': 'leandro@example.com',
        'telefono': '123456789',
        'edad': 30,
        'altura': 180,
        'peso': 75
    }
}

# Ruta del perfil
@main.route("/perfil/<int:id>")
def perfil(id):
    atleta = ATLETAS.get(id)
    entrenamientos = ENTRENAMIENTOS.get(id, {'planificados': [], 'realizados': []})
    hoy = datetime.today()

    # Calendario del mes actual
    primer_dia, num_dias = calendar.monthrange(hoy.year, hoy.month)
    calendario = []
    semana = []
    for i in range(1, primer_dia + 1):  # Días en blanco al inicio
        semana.append(0)

    for dia in range(1, num_dias + 1):
        fecha_str = f"{hoy.year}-{hoy.month:02d}-{dia:02d}"
        data = DIAS_CALENDARIO.get(fecha_str, {})
        iconos = []
        if data.get("tipo") == "run":
            iconos.append("🏃")
        elif data.get("tipo") == "natacion":
            iconos.append("🏊")
        elif data.get("tipo") == "bike":
            iconos.append("🚴")
        elif data.get("tipo") == "fuerza":
            iconos.append("🏋️")
        elif data.get("tipo") == "estirar":
            iconos.append("🧘")
        elif data.get("tipo") == "series":
            iconos.append("🏃‍♂️")

        semana.append({
            "numero": dia,
            "iconos": iconos,
            "bloqueado": data.get("bloqueado", False)
        })

        if len(semana) == 7:
            calendario.append(semana)
            semana = []

    if semana:
        while len(semana) < 7:
            semana.append(0)
        calendario.append(semana)

    return render_template("perfil.html",
                           atleta=atleta,
                           entrenamientos_planificados=entrenamientos["planificados"],
                           entrenamientos_realizados=entrenamientos["realizados"],
                           calendario_mensual=calendario)

# Guardar día: actividad, comentario y bloqueo
@main.route("/guardar_dia", methods=["POST"])
def guardar_dia():
    data = request.get_json()
    dia = data.get("dia")
    tipo = data.get("tipo")
    comentario = data.get("comentario")
    bloqueado = data.get("bloqueado", False)

    hoy = datetime.today()
    fecha_str = f"{hoy.year}-{hoy.month:02d}-{int(dia):02d}"

    DIAS_CALENDARIO[fecha_str] = {
        "tipo": tipo,
        "comentario": comentario,
        "bloqueado": bloqueado
    }

    return jsonify(success=True)

# Obtener detalles de un día
@main.route("/detalles_dia/<int:dia>")
def detalles_dia(dia):
    hoy = datetime.today()
    fecha_str = f"{hoy.year}-{hoy.month:02d}-{dia:02d}"
    datos = DIAS_CALENDARIO.get(fecha_str, {
        "tipo": "",
        "comentario": "",
        "bloqueado": False
    })
