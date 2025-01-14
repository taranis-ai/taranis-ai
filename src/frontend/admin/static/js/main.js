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