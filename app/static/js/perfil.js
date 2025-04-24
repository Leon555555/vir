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

  // Mostrar modal para editar día del calendario
  document.querySelectorAll(".day-cell").forEach(td => {
    td.addEventListener("click", () => {
      const dia = td.dataset.dia;
      fetch(`/detalles_dia/${dia}`)
        .then(res => res.json())
        .then(data => {
          document.getElementById("modal-dia-title").innerText = `Editar día ${dia}`;
          document.getElementById("comentario").value = data.comentario || "";
          document.getElementById("checkbox-bloquear").checked = data.bloqueado;
          document.getElementById("tipo-entrenamiento").value = data.tipo || "";
          document.getElementById("dia-seleccionado").value = dia;

          const modal = new bootstrap.Modal(document.getElementById("modalDia"));
          modal.show();
        });
    });
  });

  // Guardar cambios del día (actividad, comentario, bloqueado)
  document.getElementById("guardar-dia").addEventListener("click", () => {
    const dia = document.getElementById("dia-seleccionado").value;
    const tipo = document.getElementById("tipo-entrenamiento").value;
    const comentario = document.getElementById("comentario").value;
    const bloqueado = document.getElementById("checkbox-bloquear").checked;

    fetch("/guardar_dia", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dia, tipo, comentario, bloqueado })
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

  // Mostrar modal con botones al hacer clic en "Ver"
  document.querySelectorAll(".ver-detalle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const detalle = btn.dataset.detalle || "Sin descripción";
      document.getElementById("modal-dia-detalle").innerText = detalle;

      const modal = new bootstrap.Modal(document.getElementById("modalVerEntrenamiento"));
      modal.show();
    });
  });

  // Botones de acción (simulan acción por ahora)
  document.getElementById("btn-realizado").addEventListener("click", () => {
    alert("✔ Entrenamiento marcado como realizado");
  });

  document.getElementById("btn-no-realizado").addEventListener("click", () => {
    alert("✖ Entrenamiento marcado como no realizado");
  });
});
