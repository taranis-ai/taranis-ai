function getCSRFToken() {
    return document.cookie
            .split("; ")
            .find((row) => row.startsWith("csrf_access_token="))
            ?.split("=")[1];
}

function getConfirmOptions(el, question) {
  const title = el.getAttribute('data-confirm-title') || question;
  return {
    title,
    text:    title === question ? '' : question,
    icon:    el.getAttribute('data-confirm-icon') || 'question',
    confirmButtonText: el.getAttribute('data-confirm-confirm') || 'OK',
    cancelButtonText:  el.getAttribute('data-confirm-cancel')  || 'Cancel'
  };
}

function showConfirmDialog(opts) {
  return Swal.fire({ ...opts, showCancelButton: true });
}

document.body.addEventListener('htmx:confirm', function(evt) {
  if (evt.detail.elt.matches('[data-swal-confirm]')) {
    return;
  }

  evt.preventDefault();
  if (!evt.target.hasAttribute('hx-confirm')) {
    return evt.detail.issueRequest(true);
  }
  const opts = getConfirmOptions(evt.target, evt.detail.question);
  showConfirmDialog(opts).then(r => r.isConfirmed && evt.detail.issueRequest(true));
});

document.body.addEventListener('htmx:configRequest', function(evt) {
    evt.detail.headers['X-CSRF-TOKEN'] = getCSRFToken(); // add CSRF to every request
});

document.body.addEventListener('htmx:beforeSwap', function(evt) {
  evt.detail.shouldSwap = true;
});
