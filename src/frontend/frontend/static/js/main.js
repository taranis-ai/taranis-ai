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
    return globalThis.localStorage.getItem(viewportWarningStorageKey) ===
      "true";
  } catch {
    return false;
  }
}

function saveViewportWarningDismissed(value) {
  try {
    if (value) {
      globalThis.localStorage.setItem(viewportWarningStorageKey, "true");
    } else {
      globalThis.localStorage.removeItem(viewportWarningStorageKey);
    }
  } catch {
    // Ignore storage failures; the warning will still behave within this page load.
  }
}

function isBelowWxgaPlus(
  width = globalThis.innerWidth,
  height = globalThis.innerHeight,
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
  globalThis.addEventListener("resize", updateViewportWarningBar, {
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

function buildOnboardingFormData(tourId, status) {
  const formData = new FormData();
  formData.set(`settings[completed_onboarding_tours][${tourId}]`, status);
  return formData;
}

function saveOnboardingTour(root, tourId, status) {
  const settingsAction = root.dataset.settingsAction;
  if (!settingsAction) {
    return Promise.resolve();
  }

  return fetch(settingsAction, {
    method: "PATCH",
    body: buildOnboardingFormData(tourId, status),
    credentials: "same-origin",
    headers: {
      "HX-Request": "true",
      "X-CSRF-TOKEN": getCSRFToken() || "",
    },
  }).catch((error) => {
    console.error("Failed to save onboarding tour state", error);
  });
}

function existingTourSteps(steps) {
  return steps.filter((step) =>
    !step.element || document.querySelector(step.element)
  );
}

function adminWelcomeTourSteps() {
  return existingTourSteps([
    {
      element: '[data-tour-target="admin-dashboard"]',
      popover: {
        title: "Admin Dashboard",
        description:
          "Review system health, worker status, release information, and scheduled task counts from here.",
        side: "bottom",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-osint-source"]',
      popover: {
        title: "OSINT Source",
        description:
          "Configure the feeds and collectors that bring information into Taranis AI.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-bot"]',
      popover: {
        title: "Bot",
        description:
          "Manage automated analysis and processing steps that run after collection.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-scheduler"]',
      popover: {
        title: "Scheduler",
        description:
          "Inspect queues, scheduled jobs, active work, failures, and execution history.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-role"]',
      popover: {
        title: "Role",
        description:
          "Define permission sets that control what users can access and change.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-user"]',
      popover: {
        title: "User",
        description: "Create users, assign roles, and manage account access.",
        side: "right",
        align: "start",
      },
    },
    {
      popover: {
        title: "Welcome tour complete",
        description:
          "Complete this tour now, or continue with advanced administration areas.",
      },
    },
  ]);
}

function adminAdvancedTourSteps() {
  return existingTourSteps([
    {
      element: '[data-tour-target="admin-menu-report-item-type"]',
      popover: {
        title: "Report Item Type",
        description:
          "Shape report structures and the fields analysts complete during reporting.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-template"]',
      popover: {
        title: "Template",
        description:
          "Maintain presenter templates used to generate reports and products.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-product-type"]',
      popover: {
        title: "Product Type",
        description: "Configure how products are rendered from report content.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-publisher-preset"]',
      popover: {
        title: "Publisher Preset",
        description: "Set reusable publishing destinations and parameters.",
        side: "right",
        align: "start",
      },
    },
    {
      element: '[data-tour-target="admin-menu-word-list"]',
      popover: {
        title: "Word List",
        description:
          "Maintain reusable terms for collection, filtering, tagging, and enrichment.",
        side: "right",
        align: "start",
      },
    },
  ]);
}

function makeAdvancedTourButton(root, startAdvancedTour) {
  if (root.dataset.advancedCompleted === "true") {
    return null;
  }

  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-outline btn-sm";
  button.textContent = "Advanced tour";
  button.dataset.testid = "admin-onboarding-advanced-tour";
  button.addEventListener("click", startAdvancedTour);
  return button;
}

function startAdminOnboardingTour(root, tourName) {
  if (!root || typeof globalThis.driver !== "function") {
    return;
  }

  const welcomeTourId = root.dataset.welcomeTourId;
  const advancedTourId = root.dataset.advancedTourId;
  const isAdvancedTour = tourName === "advanced";
  const tourId = isAdvancedTour ? advancedTourId : welcomeTourId;
  const completionDataKey = isAdvancedTour
    ? "advancedCompleted"
    : "welcomeCompleted";
  const steps = isAdvancedTour
    ? adminAdvancedTourSteps()
    : adminWelcomeTourSteps();

  if (
    !tourId || root.dataset[completionDataKey] === "true" || steps.length === 0
  ) {
    return;
  }

  let persisted = false;
  function markTour(status) {
    if (persisted) {
      return;
    }
    persisted = true;
    root.dataset[completionDataKey] = "true";
    void saveOnboardingTour(root, tourId, status);
  }

  function closeTour(status) {
    markTour(status);
    driverObj.destroy();
  }

  const driverObj = globalThis.driver({
    steps,
    showProgress: true,
    showButtons: ["next", "previous", "close"],
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: isAdvancedTour ? "Complete advanced tour" : "Complete now",
    overlayOpacity: 0.55,
    overlayClickBehavior: () => closeTour("dismissed"),
    smoothScroll: true,
    stagePadding: 6,
    stageRadius: 4,
    disableActiveInteraction: true,
    onNextClick: () => {
      if (driverObj.isLastStep()) {
        closeTour("completed");
        return;
      }
      driverObj.moveNext();
    },
    onPrevClick: () => {
      if (driverObj.hasPreviousStep()) {
        driverObj.movePrevious();
      }
    },
    onCloseClick: () => closeTour("dismissed"),
    onDestroyStarted: () => {
      markTour("dismissed");
      driverObj.destroy();
    },
    onPopoverRender: (popover) => {
      if (isAdvancedTour || !driverObj.isLastStep()) {
        return;
      }
      const advancedButton = makeAdvancedTourButton(
        root,
        () => {
          closeTour("completed");
          setTimeout(
            () => startAdminOnboardingTour(root, "advanced"),
            150,
          );
        },
      );
      if (advancedButton) {
        popover.footerButtons.insertBefore(advancedButton, popover.nextButton);
      }
    },
  });

  driverObj.drive();
}

function startAdminTours(root) {
  if (
    !root || root.dataset.started === "true" ||
    root.dataset.welcomeCompleted === "true"
  ) {
    return;
  }
  root.dataset.started = "true";
  requestAnimationFrame(() => startAdminOnboardingTour(root, "welcome"));
}

globalThis.TaranisOnboarding = {
  startAdminTours,
  startAdminTour: startAdminOnboardingTour,
};

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

globalThis.initChoices = initChoices;
