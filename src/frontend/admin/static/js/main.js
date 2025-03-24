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

function toggleSelect() {
    let checkboxes = document.getElementsByName('cb[]');
    let checkboxes_array = Array.from(checkboxes);
    let allChecked = checkboxes_array.every(checkbox => checkbox.checked);
    this.selectedusers = [];
    for (let checkbox of checkboxes) {
        checkbox.checked = !allChecked;
        if (checkbox.checked) {
            this.selectedusers.push(checkbox.value);
        }
    }
}