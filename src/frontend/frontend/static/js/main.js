function getCookieValue(name) {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith(`${name}=`))
    ?.split("=")[1];
}

function getCSRFToken() {
  const cookieName = document.body?.dataset.csrfCookieName;
  return cookieName ? getCookieValue(cookieName) : undefined;
}

function getConfirmOptions(el, question) {
  const documentLabels = document.body?.dataset || {};
  const title = el.getAttribute("data-confirm-title") || question;
  const confirmButtonText = el.getAttribute("data-confirm-confirm") ||
    (el.hasAttribute("hx-delete")
      ? documentLabels.confirmDelete
      : documentLabels.confirmOk);
  return {
    title,
    text: title === question ? "" : question,
    icon: el.getAttribute("data-confirm-icon") || "question",
    confirmButtonText,
    cancelButtonText: el.getAttribute("data-confirm-cancel") ||
      documentLabels.confirmCancel,
  };
}

function showConfirmDialog(opts, target) {
  return Swal.fire({ ...opts, target, showCancelButton: true });
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
        window.location.href = `${this.searchUrl}?q=${
          encodeURIComponent(query)
        }`;
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

function syncSelectedStoryCardState(storyList, selectedItems) {
  if (!(storyList instanceof Element)) {
    return;
  }

  const selectedIds = new Set(selectedItems);
  storyList.querySelectorAll("article[data-story-id]").forEach((node) => {
    const selected = selectedIds.has(node.dataset.storyId);
    const read = node.dataset.storyRead === "true";
    node.classList.toggle("bg-primary/5", selected);
    node.classList.toggle("border-primary", selected || !read);
    node.classList.toggle("border-base-200", !selected && read);
    node.classList.toggle("shadow-md", selected);
    node.setAttribute("aria-selected", selected.toString());
  });
}

function canUseAssessShortcut(event, key = null) {
  if (event?.defaultPrevented) {
    return false;
  }

  const target = event?.target;
  if (
    target instanceof Element &&
    target.closest("input, textarea, select, [contenteditable], dialog")
  ) {
    return false;
  }

  if (document.querySelector("dialog[open]")) {
    return false;
  }

  return key === null ||
    (event?.shiftKey && event?.key?.toLowerCase() === key.toLowerCase());
}

function preventAssessShortcutDefault(event, code) {
  if (
    event?.shiftKey &&
    event?.code === code &&
    canUseAssessShortcut(event)
  ) {
    event.preventDefault();
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initViewportWarningBar, {
    once: true,
  });
} else {
  initViewportWarningBar();
}

document.body.addEventListener("htmx:confirm", function (evt) {
  const ctx = evt.detail.ctx;
  const triggerElement = ctx?.sourceElement;

  if (
    !(triggerElement instanceof Element) ||
    !triggerElement.hasAttribute("hx-confirm")
  ) {
    return;
  }

  evt.preventDefault();
  const opts = getConfirmOptions(triggerElement, ctx.confirm);
  if (triggerElement.matches("[data-force-delete]")) {
    Object.assign(opts, {
      input: "checkbox",
      inputValue: 0,
      inputPlaceholder:
        "Force Deletion of OSINT source and all its data. This action cannot be undone.",
    });
  }
  showConfirmDialog(
    opts,
    triggerElement.closest("dialog[open]") || document.body,
  ).then((r) => {
    if (r.isConfirmed) {
      if (r.value) {
        const action = new URL(ctx.request.action, document.baseURI);
        action.searchParams.set("force", "true");
        ctx.request.action = action.href;
      }
      evt.detail.issueRequest();
    } else {
      evt.detail.dropRequest();
    }
  });
});

document.body.addEventListener("htmx:config:request", function (evt) {
  const ctx = evt.detail.ctx;
  for (const [name, values] of Object.entries(ctx.vals || {})) {
    if (Array.isArray(values)) {
      ctx.request.body.delete(name);
      values.forEach((value) => ctx.request.body.append(name, value));
    }
  }
  ctx.request.headers["X-CSRF-TOKEN"] = getCSRFToken(); // add CSRF to every request
});

function replaceNotificationBarFromResponse(responseText) {
  const currentNotificationBar = document.getElementById("notification-bar");

  if (!currentNotificationBar || !responseText) {
    return;
  }

  const responseDoc = new DOMParser().parseFromString(
    responseText,
    "text/html",
  );
  const message = responseDoc
    .querySelector("#notification-bar #notification-message")
    ?.textContent.trim();

  if (!message) {
    return;
  }

  const responseAlert = responseDoc.querySelector("#notification-bar .alert");
  const level =
    ["error", "warning", "success", "info"].find((level) =>
      responseAlert?.classList.contains(`alert-${level}`)
    ) || "info";
  const nextNotificationBar = currentNotificationBar.cloneNode(false);
  const alert = document.createElement("div");
  alert.className = `alert alert-${level}`;
  alert.setAttribute("role", "alert");
  alert.textContent = message;

  nextNotificationBar.append(alert);
  currentNotificationBar.replaceWith(nextNotificationBar);
  self.taranisNotifications?.add({ message, level });
}

document.body.addEventListener("htmx:response:error", function (evt) {
  replaceNotificationBarFromResponse(evt.detail.ctx?.text || "");
});

function restoreSearchAfterSwap(ctx) {
  const owner = ctx?.target?.parentElement;
  if (!owner) {
    return;
  }

  function cleanup() {
    owner.removeEventListener("htmx:after:swap", restore);
    owner.removeEventListener("htmx:finally:request", finish);
  }

  function restore(evt) {
    if (evt.detail.ctx !== ctx) {
      return;
    }
    cleanup();
    const target = ctx.target.isConnected
      ? ctx.target
      : document.getElementById(ctx.target.id);
    const input = target?.querySelector("[data-search-from-request]");
    if (!input) {
      return;
    }
    input.value = new URL(ctx.request.action, location.href).searchParams.get(
      "search",
    ) || "";
    if (input.hasAttribute("data-focus-after-swap")) {
      input.focus();
    }
  }

  function finish(evt) {
    if (evt.detail.ctx === ctx) {
      cleanup();
    }
  }

  owner.addEventListener("htmx:after:swap", restore);
  owner.addEventListener("htmx:finally:request", finish);
}

function initChoices(elementID, config = {}) {
  const select = document.getElementById(elementID);
  if (!select || select.classList.contains("choices__input")) {
    return;
  }
  if (!config || typeof config !== "object") {
    config = {};
  }

  const classNames = {
    containerOuter: ["choices", "w-full"],
    containerInner: ["choices__inner"],
    input: ["choices__input"],
    inputCloned: ["choices__input--cloned"],
    list: ["choices__list"],
    itemSelectable: [
      "choices__item--selectable",
      "choices-item-selectable-primary",
    ],
    itemChoice: ["choices__item--choice"],
    selectedState: ["is-selected", "choices-selected-primary"],
  };

  const defaultConfig = {
    removeItemButton: true,
    placeholderValue: select.dataset.choicesPlaceholderValue,
    noResultsText: select.dataset.choicesNoResultsText,
    noChoicesText: select.dataset.choicesNoChoicesText,
    itemSelectText: select.dataset.choicesItemSelectText,
    classNames: classNames,
  };

  const finalConfig = Object.assign({}, defaultConfig, config);
  return new Choices(select, finalConfig);
}

self.initChoices = initChoices;
