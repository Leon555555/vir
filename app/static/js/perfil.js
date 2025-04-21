document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".dia-calendario").forEach(td => {
    td.addEventListener("click", () => {
      const dia = td.dataset.dia;
      const iconos = [...td.querySelectorAll("div:not(:first-child)")].map(div => div.textContent.trim()).join(" ");
      document.getElementById("modalDiaTitulo").innerText = `Entrenamientos día ${dia}`;
      document.getElementById("modalEntrenamientosTexto").innerText = iconos || "Sin entrenamientos";
      document.getElementById("comentarioDia").value = "";
      document.getElementById("bloquearDiaCheck").checked = false;
      new bootstrap.Modal(document.getElementById("modalDiaCalendario")).show();
    });
  });

  document.querySelectorAll(".ver-detalle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const detalle = btn.dataset.detalle || "Sin descripción";
      const tipo = btn.dataset.tipo || "Entrenamiento";
      const dia = btn.dataset.dia || "";
      document.getElementById("modalDiaTitulo").innerText = `${tipo.charAt(0).toUpperCase() + tipo.slice(1)} - día ${dia}`;
      document.getElementById("modalEntrenamientosTexto").innerText = detalle;
      document.getElementById("comentarioDia").value = "";
      document.getElementById("bloquearDiaCheck").checked = false;
    });
  });
});
