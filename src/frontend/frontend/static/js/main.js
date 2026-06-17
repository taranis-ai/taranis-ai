function getCSRFToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrf_access_token="))
    ?.split("=")[1];
}

function getConfirmOptions(el, question) {
  const title = el.getAttribute("data-confirm-title") || question;
  const confirmButtonText = el.getAttribute("data-confirm-confirm") ||
    (el.hasAttribute("hx-delete") ? "Delete" : "OK");
  return {
    title,
    text: title === question ? "" : question,
    icon: el.getAttribute("data-confirm-icon") || "question",
    confirmButtonText,
    cancelButtonText: el.getAttribute("data-confirm-cancel") || "Cancel",
  };
}

function showConfirmDialog(opts) {
  return Swal.fire({ ...opts, showCancelButton: true });
}

const viewportWarningStorageKey = "taranis.viewportWarningDismissed";

function loadViewportWarningDismissed() {
  try {
    return self.localStorage.getItem(viewportWarningStorageKey) ===
      "true";
  } catch {
    return false;
  }
}

function saveViewportWarningDismissed(value) {
  try {
    if (value) {
      self.localStorage.setItem(viewportWarningStorageKey, "true");
    } else {
      self.localStorage.removeItem(viewportWarningStorageKey);
    }
  } catch {
    // Ignore storage failures; the warning will still behave within this page load.
  }
}

function isBelowWxgaPlus(
  width = self.innerWidth,
  height = self.innerHeight,
) {
  return width < 1440 || height < 600;
}

let viewportWarningDismissed = loadViewportWarningDismissed();

function updateViewportWarningBar() {
  const bar = document.getElementById("viewport-notification");
  const visible = isBelowWxgaPlus();
  const shouldShow = visible && !viewportWarningDismissed;

  if (!visible) {
    viewportWarningDismissed = false;
    saveViewportWarningDismissed(false);
  }

  if (!bar) {
    document.documentElement.style.setProperty(
      "--viewport-warning-height",
      "0px",
    );
    return;
  }

  bar.classList.toggle("hidden", !shouldShow);
  document.documentElement.style.setProperty(
    "--viewport-warning-height",
    shouldShow ? `${bar.offsetHeight}px` : "0px",
  );
}

function initViewportWarningBar() {
  const bar = document.getElementById("viewport-notification");

  if (bar) {
    bar.addEventListener("click", () => {
      viewportWarningDismissed = true;
      saveViewportWarningDismissed(true);
      updateViewportWarningBar();
    });
  }

  document
    .querySelectorAll("[data-viewport-warning-reset-on-logout]")
    .forEach((element) => {
      element.addEventListener("click", () => {
        viewportWarningDismissed = false;
        saveViewportWarningDismissed(false);
      });
    });

  updateViewportWarningBar();
  self.addEventListener("resize", updateViewportWarningBar, {
    passive: true,
  });
}

function omniSearch(searchUrl) {
  return {
    searchUrl,
    open: false,
    applyOmniSearch(query) {
      const input = this.$refs.omniInput;
      input.value = query;
      this.open = true;
      input.focus();
      input.dispatchEvent(new Event("input", { bubbles: true }));
    },
    submitOmniSearch() {
      const query = this.$refs.omniInput.value.trim();
      if (query) {
        window.location.href = `${this.searchUrl}?q=${encodeURIComponent(query)}`;
      }
    },
    focusShortcut(event) {
      if (event.key !== "/") {
        return;
      }
      if (["INPUT", "TEXTAREA", "SELECT"].includes(event.target.tagName)) {
        return;
      }
      event.preventDefault();
      this.$refs.omniInput.focus();
      this.$refs.omniInput.select();
    },
  };
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initViewportWarningBar, {
    once: true,
  });
} else {
  initViewportWarningBar();
}

document.body.addEventListener("htmx:confirm", function (evt) {
  const triggerElement = evt.detail.elt;

  if (
    !(triggerElement instanceof Element) ||
    !triggerElement.hasAttribute("hx-confirm")
  ) {
    return;
  }

  if (triggerElement.matches("[data-swal-confirm]")) {
    return;
  }

  evt.preventDefault();
  const opts = getConfirmOptions(triggerElement, evt.detail.question);
  showConfirmDialog(opts).then((r) => {
    if (r.isConfirmed) {
      evt.detail.issueRequest(true);
    }
  });
});

document.body.addEventListener("htmx:configRequest", function (evt) {
  evt.detail.headers["X-CSRF-TOKEN"] = getCSRFToken(); // add CSRF to every request
});

function replaceNotificationBarFromResponse(responseText) {
  const currentNotificationBar = document.getElementById("notification-bar");

  if (!currentNotificationBar || !responseText) {
    return;
  }

  const responseDoc = new DOMParser().parseFromString(responseText, "text/html");
  const message = responseDoc
    .querySelector("#notification-bar #notification-message")
    ?.textContent.trim();

  if (!message) {
    return;
  }

  const nextNotificationBar = currentNotificationBar.cloneNode(false);
  const alert = document.createElement("div");
  alert.className = responseDoc.querySelector("#notification-bar .alert-error")
    ? "alert alert-error"
    : "alert alert-info";
  alert.setAttribute("role", "alert");
  alert.textContent = message;

  nextNotificationBar.append(alert);
  currentNotificationBar.replaceWith(nextNotificationBar);
}

document.body.addEventListener("htmx:responseError", function (evt) {
  replaceNotificationBarFromResponse(evt.detail.xhr?.responseText || "");
});

function initChoices(elementID, placeholder = "items", config = {}) {
  const select = document.getElementById(elementID);
  if (!select || select.classList.contains("choices__input")) {
    return;
  }

  const classNames = {
    containerOuter: ["choices", "!bg-base-200"],
    containerInner: ["choices__inner", "!bg-base-200"],
    input: ["choices__input", "!bg-base-200"],
    inputCloned: ["choices__input--cloned", "!bg-base-200"],
    list: ["choices__list", "!bg-base-200"],
    itemSelectable: [
      "choices__item--selectable",
      "choices-item-selectable-primary",
    ],
    itemChoice: ["choices__item--choice", "!bg-base-200"],
    selectedState: ["is-selected", "choices-selected-primary"],
  };

  const defaultConfig = {
    removeItemButton: true,
    placeholderValue: "Select " + placeholder,
    noResultsText: "No " + placeholder + " found",
    noChoicesText: "No " + placeholder + " to choose from",
    classNames: classNames,
  };

  const finalConfig = Object.assign({}, defaultConfig, config);
  return new Choices(select, finalConfig);
}

self.initChoices = initChoices;
