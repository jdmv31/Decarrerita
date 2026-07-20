document.addEventListener("DOMContentLoaded", function() {
    
    const latDefecto = 8.2954;
    const lngDefecto = -62.7197;
    let latOrigen, lngOrigen;
    let controlRuta = null;

    const btnSolicitar = document.getElementById('btn_solicitar');
    const textoInstrucciones = document.getElementById('instrucciones');

    const mapa = L.map('mi_mapa').setView([latDefecto, lngDefecto], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: 'OpenStreetMap'
    }).addTo(mapa);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(posicion) {
                latOrigen = posicion.coords.latitude;
                lngOrigen = posicion.coords.longitude;
                
                mapa.setView([latOrigen, lngOrigen], 15);
                L.marker([latOrigen, lngOrigen]).addTo(mapa).bindPopup("Tu ubicacion actual").openPopup();
                
                textoInstrucciones.innerHTML = "Ubicacion detectada. Haz clic en el mapa para marcar tu destino.";
                
                document.getElementById('lat_origen').value = latOrigen;
                document.getElementById('lng_origen').value = lngOrigen;
            },
            function(error) {
                alert("Por favor, activa el GPS para poder solicitar un viaje.");
                textoInstrucciones.innerHTML = "No pudimos detectar tu ubicacion.";
            }
        );
    }

    mapa.on('click', function(evento) {
        if (!latOrigen || !lngOrigen) {
            alert("Espera a que detectemos tu ubicacion antes de marcar el destino.");
            return;
        }

        const latDestino = evento.latlng.lat;
        const lngDestino = evento.latlng.lng;

        if (controlRuta !== null) {
            mapa.removeControl(controlRuta);
        }

        textoInstrucciones.innerHTML = "Calculando ruta...";
        btnSolicitar.disabled = true;
        btnSolicitar.innerText = "Calculando...";

        controlRuta = L.Routing.control({
            waypoints: [
                L.latLng(latOrigen, lngOrigen),
                L.latLng(latDestino, lngDestino)
            ],
            show: false,
            addWaypoints: false,
            routeWhileDragging: false,
            fitSelectedRoutes: true,
            lineOptions: {
                styles: [{color: '#007bff', opacity: 0.8, weight: 5}]
            }
        }).addTo(mapa);

        controlRuta.on('routesfound', function(e) {
            const rutaIdeal = e.routes[0];
            const distanciaMetros = rutaIdeal.summary.totalDistance;
            const distanciaKm = (distanciaMetros / 1000).toFixed(2);
            const tiempoMinutos = Math.round(rutaIdeal.summary.totalTime / 60);

            document.getElementById('lat_destino').value = latDestino;
            document.getElementById('lng_destino').value = lngDestino;
            document.getElementById('distancia_km').value = distanciaKm;
            document.getElementById('tiempo_minutos').value = tiempoMinutos;

            textoInstrucciones.innerHTML = `Ruta trazada: ${distanciaKm} km (Aprox. ${tiempoMinutos} min)`;
            
            btnSolicitar.innerText = "Confirmar y Pedir Viaje";
            btnSolicitar.disabled = false;
        });
    });
});