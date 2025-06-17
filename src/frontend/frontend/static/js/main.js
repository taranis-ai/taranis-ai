function getCSRFToken() {
    return document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrf_access_token="))
            ?.split("=")[1];
}


document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-CSRF-TOKEN'] = getCSRFToken(); // add CSRF to every request
});
function toggleDetails(jobId) {
    const jobRow = document.getElementById(`job-row-${jobId}`);
    const detailsRow = document.getElementById(`details-${jobId}`);
    const isExpanded = jobRow.getAttribute('data-expanded') === 'true';

    if (isExpanded) {
        detailsRow.classList.add('hidden');
        jobRow.setAttribute('data-expanded', 'false');
    } else {
        detailsRow.classList.remove('hidden');
        jobRow.setAttribute('data-expanded', 'true');
    }
}

// hide debug menu if loaded inside iframe

if (window.self !== window.top) {
  const adminMenu = document.getElementById('admin_menu');
  const navbar = document.getElementById('navbar');
  if (adminMenu) {
    adminMenu.remove();
  }
  if (navbar) {
    navbar.remove();
  }
}
