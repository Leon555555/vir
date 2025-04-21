document.addEventListener("DOMContentLoaded", () => {
  const botones = document.querySelectorAll("[data-section]");
  const secciones = {
    home: document.getElementById("seccion-home"),
    datos: document.getElementById("seccion-datos"),
    editar: document.getElementById("seccion-editar")
  };

  botones.forEach(btn => {
    btn.addEventListener("click", () => {
      botones.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      Object.values(secciones).forEach(s => s.classList.add("d-none"));
      secciones[btn.dataset.section].classList.remove("d-none");
    });
  });

  document.querySelectorAll(".ver-detalle-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const tipo = btn.dataset.tipo;
      const detalle = btn.dataset.detalle;
      const iconos = {
        "carrera": "🏃", "bicicleta": "🚴", "natación": "🏊‍♂️",
        "fuerza": "💪", "descanso": "😴", "series pista": "🏟️", "estiramientos": "🤸"
      };
      const icono = iconos[tipo.toLowerCase()] || "🏃";
      document.getElementById("modalEntrenamientoTitulo").textContent = `${icono} ${tipo}`;
      document.getElementById("modalEntrenamientoDetalle").textContent = detalle;
    });
  });

  document.querySelectorAll(".calendario-dia").forEach(td => {
    td.addEventListener("click", () => {
      const dia = td.dataset.dia;
      const iconos = Array.from(td.querySelectorAll("div")).slice(1).map(div => div.textContent).join(" ");
      document.getElementById("modalEntrenamientoTitulo").textContent = `Entrenamientos día ${dia}`;
      document.getElementById("modalEntrenamientoDetalle").innerHTML = `Entrenamientos: ${iconos}`;
      new bootstrap.Modal(document.getElementById("modalEntrenamiento")).show();
    });
  });
});
