new MutationObserver(
	function() {
		document.querySelector('title').textContent = "TARANIS NG";
	}).observe(
		document.querySelector('title'),{ childList: true }
	);
