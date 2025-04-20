let ejercicios = ["Flexiones", "Sentadillas"];
let ejercicioActual = 0;
let intervalo;
let trabajando = true;

function iniciarTabata() {
    let trabajo = parseInt(document.getElementById("tiempoTrabajo").value);
    let descanso = parseInt(document.getElementById("tiempoDescanso").value);

    ejercicioActual = 0;
    trabajando = true;
    ejecutarEjercicio(trabajo, descanso);
}

function ejecutarEjercicio(trabajo, descanso) {
    if (ejercicioActual >= ejercicios.length) {
        document.getElementById("faseActual").innerText = "🎉 ¡Finalizado!";
        document.getElementById("contador").innerText = "";
        document.getElementById("nombreEjercicio").innerText = "";
        return;
    }

    let tiempo = trabajando ? trabajo : descanso;
    let nombre = ejercicios[ejercicioActual];

    document.getElementById("faseActual").innerText = trabajando ? "💪 ¡Trabaja!" : "🧘 Descansa";
    document.getElementById("nombreEjercicio").innerText = trabajando ? nombre : "";
    document.getElementById("contador").innerText = tiempo;

    intervalo = setInterval(() => {
        tiempo--;
        document.getElementById("contador").innerText = tiempo;

        if (tiempo <= 0) {
            clearInterval(intervalo);
            if (!trabajando) ejercicioActual++;
            trabajando = !trabajando;
            ejecutarEjercicio(trabajo, descanso);
        }
    }, 1000);
}
