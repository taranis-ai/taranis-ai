function getCSRFToken() {
    return document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrf_access_token="))
            ?.split("=")[1];
}


document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-CSRF-TOKEN'] = getCSRFToken(); // add CSRF to every request
});

document.body.addEventListener('htmx:confirm', function(event) {
    event.preventDefault();
    if (!event.target.hasAttribute('hx-confirm')) {
        event.detail.issueRequest(true);
        return;
    }
    const el = event.target;

    const title = el.getAttribute('data-confirm-title') || event.detail.question;
    const text = title === event.detail.question ? '' : event.detail.question;
    const icon = el.getAttribute('data-confirm-icon') || 'question';
    const confirmButtonText = el.getAttribute('data-confirm-confirm') || 'OK';
    const cancelButtonText = el.getAttribute('data-confirm-cancel') || 'Cancel';

    Swal.fire({
        title: title,
        text: text,
        icon: icon,
        showCancelButton: true,
        confirmButtonText: confirmButtonText,
        cancelButtonText: cancelButtonText
    }).then((result) => {
        if (result.isConfirmed) {
            event.detail.resume();
        }
    });
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
