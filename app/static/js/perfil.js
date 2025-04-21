// perfil.js
document.addEventListener("DOMContentLoaded", () => {
  const botones = document.querySelectorAll("[data-section]");
  const secciones = {
    home: document.getElementById("seccion-home"),
    datos: document.getElementById("seccion-datos"),
    editar: document.getElementById("seccion-editar"),
  };
  botones.forEach((btn) => {
    btn.addEventListener("click", () => {
      botones.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const target = btn.dataset.section;
      for (const key in secciones) {
        secciones[key].classList.add("d-none");
      }
      secciones[target].classList.remove("d-none");
    });
  });

  // Mostrar y ocultar barra lateral
  const menuBtn = document.getElementById("menu-btn");
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.getElementById("main-content");

  if (menuBtn && sidebar && mainContent) {
    menuBtn.addEventListener("click", () => {
      sidebar.classList.toggle("d-none");
      mainContent.classList.toggle("col-md-9");
      mainContent.classList.toggle("col-md-12");
    });
  }

  // Modal eventos
  let entrenamientoId;
  document.querySelectorAll(".ver-detalle-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const detalle = btn.dataset.detalle;
      entrenamientoId = btn.dataset.id;
      const stravaLink = btn.dataset.strava || "#";
      document.getElementById("detalle-entrenamiento").innerText =
        detalle || "Sin descripción";
      document.getElementById("strava-btn").href = stravaLink;
    });
  });

  const realizadoBtn = document.getElementById("btn-realizado");
  if (realizadoBtn) {
    realizadoBtn.addEventListener("click", () => {
      fetch("/marcar_realizado_ajax", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ id: entrenamientoId }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            location.reload();
          } else {
            alert("Error al marcar como realizado");
          }
        });
    });
  }
});
