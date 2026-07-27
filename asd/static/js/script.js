function cambiarFormulario(event) {
    // Esto evita que el navegador intente hacer otra cosa (como recargar la página)
    if(event) event.preventDefault();

    // Buscamos la tarjeta
    const tarjeta = document.getElementById('tarjeta-login-registro');
    
    // Verificamos si realmente la encontró antes de intentar girarla
    if (tarjeta) {
        tarjeta.classList.toggle('girada');
        console.log("¡El Javascript funcionó! Se aplicó la clase 'girada'.");
    } else {
        console.error("Fallo de JS: No se encontró el elemento con ID 'tarjeta-login-registro'.");
    }
}