function getCSRFToken() {
    return document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrf_access_token="))
            ?.split("=")[1];
}


document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-CSRF-TOKEN'] = getCSRFToken(); // add CSRF to every request
});
