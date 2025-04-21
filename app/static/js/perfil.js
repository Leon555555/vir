document.addEventListener("DOMContentLoaded", () => {
  // Mostrar modal al hacer click en un día
  document.querySelectorAll(".calendar-day").forEach(td => {
    td.addEventListener("click", () => {
      const dia = td.dataset.dia;
      document.getElementById("modal-dia-numero").innerText = dia;
      document.getElementById("comentario-dia").value = ""; // opcional cargar comentario actual
      document.getElementById("bloquear-dia").checked = td.classList.contains("bg-danger");
      new bootstrap.Modal(document.getElementById("modalDia")).show();
    });
  });

  // Guardar bloqueo
  document.getElementById("guardar-dia-btn").addEventListener("click", () => {
    const dia = document.getElementById("modal-dia-numero").innerText;
    const comentario = document.getElementById("comentario-dia").value;
    const bloqueado = document.getElementById("bloquear-dia").checked;

    fetch("/guardar_bloqueo", {
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
});
