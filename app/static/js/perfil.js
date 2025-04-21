document.addEventListener("DOMContentLoaded", () => {
  // Toggle secciones
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
      for (const key in secciones) {
        secciones[key].classList.add("d-none");
      }
      secciones[btn.dataset.section].classList.remove("d-none");
    });
  });

  // Modal
  let entrenamientoId;
  document.querySelectorAll('.ver-detalle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      entrenamientoId = btn.dataset.id;
      const detalle = btn.dataset.detalle || 'Sin descripción';
      document.getElementById('detalle-entrenamiento').innerText = detalle;
      document.getElementById('strava-btn').href = btn.dataset.strava || '#';
    });
  });

  document.getElementById('btn-realizado').addEventListener('click', () => {
    fetch('/marcar_realizado_ajax', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ id: entrenamientoId })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) location.reload();
      else alert('Error al marcar como realizado');
    });
  });

  // Toggle sidebar
  document.getElementById("menu-toggle").addEventListener("click", () => {
    const sidebar = document.getElementById("sidebar");
    sidebar.classList.toggle("collapsed");
  });
});
