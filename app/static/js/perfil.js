// static/js/perfil.js
document.addEventListener("DOMContentLoaded", () => {
  // Navegación entre secciones
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

  // Modal entrenamiento desde botón "Ver"
  let entrenamientoId;
  document.querySelectorAll('.ver-detalle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const detalle = btn.dataset.detalle;
      entrenamientoId = btn.dataset.id;
      document.getElementById('detalle-entrenamiento').innerText = detalle || 'Sin descripción';
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

  // Clic en día del calendario
  document.querySelectorAll('.calendar-day').forEach(cell => {
    cell.addEventListener('click', () => {
      const detalle = cell.dataset.detalle;
      if (detalle && detalle.trim()) {
        document.getElementById('detalle-entrenamiento').innerText = detalle;
        const modal = new bootstrap.Modal(document.getElementById('modalEntrenamiento'));
        modal.show();
      }
    });
  });

  // Botón para mostrar/ocultar barra lateral
  const toggleBtn = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main-content');

  toggleBtn?.addEventListener('click', () => {
    sidebar.classList.toggle('d-none');
    main.classList.toggle('w-100');
  });
});
