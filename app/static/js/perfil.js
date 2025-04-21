document.addEventListener("DOMContentLoaded", () => {
  const botones = document.querySelectorAll("[data-section]");
  const secciones = {
    home: document.getElementById("seccion-home"),
    datos: document.getElementById("seccion-datos"),
    editar: document.getElementById("seccion-editar"),
  };

  botones.forEach(btn => {
    btn.addEventListener("click", () => {
      botones.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const target = btn.dataset.section;
      for (const key in secciones) {
        secciones[key].classList.add("d-none");
      }
      secciones[target].classList.remove("d-none");
    });
  });

  // Modal para detalle de entrenamiento
  let entrenamientoId = null;

  document.querySelectorAll('.ver-detalle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const detalle = btn.dataset.detalle;
      const tipo = btn.dataset.tipo;
      entrenamientoId = btn.dataset.id;
      const stravaLink = btn.dataset.strava || "#";

      document.getElementById('modalEntrenamientoLabel').textContent = tipo || "Entrenamiento";
      document.getElementById('detalle-entrenamiento').textContent = detalle || "Sin descripción";
      document.getElementById('strava-btn').href = stravaLink;
      document.getElementById('comentario').value = "";
    });
  });

  document.getElementById('btn-realizado').addEventListener('click', () => {
    const comentario = document.getElementById("comentario").value;
    fetch('/marcar_realizado_ajax', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: entrenamientoId, comentario: comentario })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        location.reload();
      } else {
        alert('Error al marcar como realizado');
      }
    });
  });
});
