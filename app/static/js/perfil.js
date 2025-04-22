document.addEventListener("DOMContentLoaded", () => {
  // Cambiar de sección
  const botones = document.querySelectorAll("[data-section]");
  const secciones = {
    home: document.getElementById("seccion-home"),
    datos: document.getElementById("seccion-datos")
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

  // Mostrar modal al hacer clic en celda del calendario
  document.querySelectorAll(".day-cell").forEach(td => {
    td.addEventListener("click", () => {
      const dia = td.dataset.dia;
      fetch(`/detalles_dia/${dia}`)
        .then(res => res.json())
        .then(data => {
          document.getElementById("modal-dia-title").innerText = `Entrenamientos día ${dia}`;
          document.getElementById("modal-dia-detalle").innerText = data.detalle || "Sin descripción";
          document.getElementById("comentario").value = data.comentario || "";
          document.getElementById("checkbox-bloquear").checked = data.bloqueado;
          document.getElementById("dia-seleccionado").value = dia;
          const modal = new bootstrap.Modal(document.getElementById("modalDia"));
          modal.show();
        });
    });
  });

  // Guardar cambios en el día
  document.getElementById("guardar-dia").addEventListener("click", () => {
    const dia = document.getElementById("dia-seleccionado").value;
    const comentario = document.getElementById("comentario").value;
    const bloqueado = document.getElementById("checkbox-bloquear").checked;

    fetch("/guardar_dia", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dia, comentario, bloqueado })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          location.reload();
        } else {
          alert("Error al guardar");
        }
      });
  });

  // Mostrar/Ocultar el menú lateral
  const menuToggle = document.getElementById("menu-toggle");
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.getElementById("main-content");

  if (menuToggle && sidebar && mainContent) {
    menuToggle.addEventListener("click", () => {
      sidebar.classList.toggle("d-none");
      mainContent.classList.toggle("w-100");
    });
  }
});
