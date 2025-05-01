document.addEventListener("DOMContentLoaded", () => {
  // Navegación entre secciones
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

  // Modal para editar día desde calendario
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

  // Guardar cambios del día
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

  // Ver detalle desde botón "Ver"
  document.querySelectorAll(".ver-detalle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const entrenamientoId = btn.dataset.id;
      const tipo = btn.dataset.tipo;
      const detalle = btn.dataset.detalle;

      document.getElementById("ver-id").value = entrenamientoId;
      document.getElementById("ver-tipo").value = tipo;
      document.getElementById("ver-detalle").value = detalle;

      const modal = new bootstrap.Modal(document.getElementById("modalVerEntrenamiento"));
      modal.show();
    });
  });

  // Marcar como realizado
  document.getElementById("btn-realizado").addEventListener("click", () => {
    actualizarEstadoEntrenamiento(true);
  });

  // Marcar como no realizado
  document.getElementById("btn-no-realizado").addEventListener("click", () => {
    actualizarEstadoEntrenamiento(false);
  });

  // Guardar cambios en tipo/detalle desde modal
  document.getElementById("btn-guardar-edicion").addEventListener("click", () => {
    const id = document.getElementById("ver-id").value;
    const tipo = document.getElementById("ver-tipo").value;
    const detalle = document.getElementById("ver-detalle").value;

    fetch(`/editar_entrenamiento/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tipo, detalle })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        location.reload();
      } else {
        alert("Error al editar entrenamiento");
      }
    });
  });

  function actualizarEstadoEntrenamiento(realizado) {
    const id = document.getElementById("ver-id").value;
    fetch(`/marcar_entrenamiento/${id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ realizado })
    })
    .then(res => res.json())
    .then(data => {
      if (data.success) {
        location.reload();
      } else {
        alert("Error al actualizar entrenamiento");
      }
    });
  }
});
