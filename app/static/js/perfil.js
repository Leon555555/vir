document.addEventListener("DOMContentLoaded", () => {
  // Cambiar entre secciones del menú lateral
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

  // Modal entrenamiento
  let entrenamientoId;
  document.querySelectorAll('.ver-detalle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const detalle = btn.dataset.detalle;
      entrenamientoId = btn.dataset.id;
      const stravaLink = btn.dataset.strava || '#';
      document.getElementById('detalle-entrenamiento').innerText = detalle || 'Sin descripción';
      document.getElementById('strava-btn').href = stravaLink;
    });
  });

  document.getElementById('btn-realizado')?.addEventListener('click', () => {
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
        alert('Error al marcar como realizado');
      }
    });
  });

  // Lógica para ocultar barra lateral
  const menuToggle = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.getElementById("main-content");

  menuToggle?.addEventListener("click", () => {
    sidebar.classList.toggle("d-none");
    mainContent.classList.toggle("expanded");
  });

  // Clic en día del calendario
  document.querySelectorAll(".calendar-day").forEach(cell => {
    cell.addEventListener("click", () => {
      const tooltip = cell.dataset.tooltip;
      if (tooltip) {
        alert("Entrenamiento: " + tooltip);
      }
    });
  });
});
