window.onload = function () {
	let target = document.getElementById('kc-form-options');
	let error_login = document.getElementById('input-error');
	let error_username = document.getElementById('input-error-username');
	let alert = document.querySelector("[class*=alert]");

	if (error_login) target.prepend(error_login);
	if (error_username) target.prepend(error_username);
	if (alert) target.prepend(alert);

}
