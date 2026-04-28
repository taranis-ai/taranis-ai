function getCSRFToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrf_access_token="))
    ?.split("=")[1];
}

function getConfirmOptions(el, question) {
  const title = el.getAttribute("data-confirm-title") || question;
  const confirmButtonText = el.getAttribute("data-confirm-confirm") || (el.hasAttribute("hx-delete") ? "Delete" : "OK");
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
    return window.localStorage.getItem(viewportWarningStorageKey) === "true";
  } catch {
    return false;
  }
}

function saveViewportWarningDismissed(value) {
  try {
    if (value) {
      window.localStorage.setItem(viewportWarningStorageKey, "true");
    } else {
      window.localStorage.removeItem(viewportWarningStorageKey);
    }
  } catch {
    // Ignore storage failures; the warning will still behave within this page load.
  }
}

function isBelowWxgaPlus(
  width = window.innerWidth,
  height = window.innerHeight,
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
  window.addEventListener("resize", updateViewportWarningBar, {
    passive: true,
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initViewportWarningBar, {
    once: true,
  });
} else {
  initViewportWarningBar();
}

document.body.addEventListener("htmx:confirm", function (evt) {
  if (!evt.target.hasAttribute("hx-confirm")) {
    return;
  }

  if (evt.detail.elt.matches("[data-swal-confirm]")) {
    return;
  }

  evt.preventDefault();
  const opts = getConfirmOptions(evt.target, evt.detail.question);
  showConfirmDialog(opts).then((r) => {
    if (r.isConfirmed) {
      evt.detail.issueRequest(true);
    }
  });
});

document.body.addEventListener("htmx:configRequest", function (evt) {
  evt.detail.headers["X-CSRF-TOKEN"] = getCSRFToken(); // add CSRF to every request
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
