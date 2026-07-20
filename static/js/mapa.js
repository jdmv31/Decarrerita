document.addEventListener("DOMContentLoaded", function() {
    
    const latDefecto = 8.2954;
    const lngDefecto = -62.7197;
    let latOrigen, lngOrigen;
    let controlRuta = null;
    
    const btnConfirmar = document.getElementById('btn_confirmar');
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

        if(btnConfirmar) {
            btnConfirmar.disabled = true;
            btnConfirmar.innerText = "Calculando...";
        }
        
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
            const distanciaKm = (rutaIdeal.summary.totalDistance / 1000).toFixed(2);
            const tiempoMinutos = Math.round(rutaIdeal.summary.totalTime / 60);
            
            document.getElementById('lat_destino').value = e.waypoints[1].latLng.lat;
            document.getElementById('lng_destino').value = e.waypoints[1].latLng.lng;
            document.getElementById('distancia_km').value = distanciaKm;
            document.getElementById('tiempo_minutos').value = tiempoMinutos;
            
            textoInstrucciones.innerHTML = "Calculando tarifa exacta...";
            
            fetch(`/api/calcular-tarifa?distancia_km=${distanciaKm}&tiempo_minutos=${tiempoMinutos}`)
                .then(response => response.json())
                .then(data => {
                    document.getElementById('val_distancia').innerText = distanciaKm;
                    document.getElementById('val_tiempo').innerText = tiempoMinutos;
                    document.getElementById('val_monto').innerText = data.costo_total;
                    document.getElementById('recuadro_info').style.display = 'block';
                    textoInstrucciones.innerHTML = "Ruta trazada. Por favor, revisa el resumen a la derecha.";

                    if(btnConfirmar) {
                        btnConfirmar.innerText = "Confirmar Viaje";
                        btnConfirmar.disabled = false;
                    }
                })
                .catch(error => {
                    console.error("Error al calcular la tarifa:", error);
                    textoInstrucciones.innerHTML = "Error al calcular el precio. Intenta de nuevo.";
                    if(btnConfirmar) {
                        btnConfirmar.innerText = "Error";
                    }
                });
        });
    });
});