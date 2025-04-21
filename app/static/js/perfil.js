document.addEventListener("DOMContentLoaded", () => {
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.getElementById("main-content");
  const menuToggle = document.getElementById("menu-toggle");

  menuToggle.addEventListener("click", () => {
    sidebar.classList.toggle("d-none");
    if (sidebar.classList.contains("d-none")) {
      mainContent.classList.remove("col-md-9");
      mainContent.classList.add("w-100");
    } else {
      mainContent.classList.add("col-md-9");
      mainContent.classList.remove("w-100");
    }
  });

  // Navegación por secciones
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

  // Modal de detalle
  let entrenamientoId;
  document.querySelectorAll('.ver-detalle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      entrenamientoId = btn.dataset.id;
      const detalle = btn.dataset.detalle;
      const strava = btn.dataset.strava || '#';

      document.getElementById('detalle-entrenamiento').innerText = detalle || 'Sin descripción';
      document.getElementById('strava-btn').href = strava;
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
      if (data.success) {
        location.reload();
      } else {
        alert("Error al marcar como realizado");
      }
    });
  });
});
