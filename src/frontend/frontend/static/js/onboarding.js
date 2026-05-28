const adminOnboardingResumeKey = "taranis.adminOnboarding.resume";

function getOnboardingCSRFToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrf_access_token="))
    ?.split("=")[1];
}

function buildOnboardingFormData(tourId, status) {
  const formData = new FormData();
  formData.set(`settings[onboarding_tours][${tourId}]`, status);
  return formData;
}

function saveOnboardingTour(root, tourId, status, options = {}) {
  const settingsAction = root.dataset.settingsAction;
  if (!settingsAction) {
    return Promise.resolve();
  }

  const body = buildOnboardingFormData(tourId, status);
  if (options.continueOnboarding) {
    body.set("continue_admin_onboarding", "true");
  }

  return fetch(settingsAction, {
    method: "PATCH",
    body,
    credentials: "same-origin",
    headers: {
      "HX-Request": "true",
      "X-CSRF-TOKEN": getOnboardingCSRFToken() || "",
    },
  }).catch((error) => {
    console.error("Failed to save onboarding tour state", error);
  });
}

function normalizeTourPath(pathname) {
  return pathname.replace(/\/+$/, "") || "/";
}

function urlsShareRoute(left, right) {
  return (
    left.origin === right.origin &&
    normalizeTourPath(left.pathname) === normalizeTourPath(right.pathname)
  );
}

function currentTourUrl() {
  return new URL(self.location.href);
}

function getTourLink(element) {
  if (!element) {
    return null;
  }
  if (element.matches?.("a[href]")) {
    return element;
  }
  return element.closest?.("a[href]") || null;
}

function linkUrl(link) {
  return new URL(link.href, self.location.href);
}

function routeLinkForStep(step) {
  if (!step.routeElement) {
    return null;
  }
  return getTourLink(document.querySelector(step.routeElement));
}

function routeUrlForStep(step) {
  if (step.route) {
    return new URL(step.route, self.location.href);
  }

  const link = routeLinkForStep(step);
  return link ? linkUrl(link) : null;
}

function isCurrentTourRoute(step) {
  const routeUrl = routeUrlForStep(step);
  return !routeUrl || urlsShareRoute(routeUrl, currentTourUrl());
}

function navigateToStepRoute(step, currentElement) {
  const routeUrl = routeUrlForStep(step);
  if (!routeUrl || urlsShareRoute(routeUrl, currentTourUrl())) {
    return false;
  }

  const currentLink = getTourLink(currentElement);
  if (currentLink && urlsShareRoute(linkUrl(currentLink), routeUrl)) {
    currentLink.click();
    return true;
  }

  const routeLink = routeLinkForStep(step);
  if (routeLink) {
    routeLink.click();
    return true;
  }

  self.location.assign(routeUrl.href);
  return true;
}

function readResumeState() {
  try {
    return JSON.parse(self.sessionStorage.getItem(adminOnboardingResumeKey));
  } catch {
    return null;
  }
}

function writeResumeState(tourName, tourId, stepId) {
  try {
    self.sessionStorage.setItem(
      adminOnboardingResumeKey,
      JSON.stringify({ tourName, tourId, stepId }),
    );
  } catch {
    // Storage can be unavailable in restricted browser modes. The tour still works on the current page.
  }
}

function clearResumeState() {
  try {
    self.sessionStorage.removeItem(adminOnboardingResumeKey);
  } catch {
    // Ignore storage failures.
  }
}

function firstMatchingElement(selectors) {
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      return element;
    }
  }
  return null;
}

function tableElement(tableId) {
  return () =>
    firstMatchingElement([
      `#${tableId}`,
      `#${tableId}-container table`,
      `#${tableId}-container`,
      ".table-container table",
      ".table-container",
    ]);
}

function osintSourceTableOrDefaultButton() {
  return firstMatchingElement([
    '[data-tour-target="admin-osint-source-load-defaults"]',
    "#osint_source-table",
    "#osint_source-table-container table",
    "#osint_source-table-container",
  ]);
}

function schedulerTableElement() {
  return firstMatchingElement([
    "#scheduled-jobs-table table",
    "#scheduled-jobs-table",
    "#active-jobs-table table",
    "#active-jobs-table",
  ]);
}

function sidebarStep(id, target, title, description) {
  return {
    id,
    element: `[data-tour-target="${target}"]`,
    popover: {
      title,
      description,
      side: "right",
      align: "start",
    },
  };
}

function routeContentStep(
  id,
  routeElement,
  element,
  title,
  description,
) {
  return {
    id,
    routeElement: `[data-tour-target="${routeElement}"]`,
    element,
    popover: {
      title,
      description,
      side: "over",
      align: "center",
    },
  };
}

function adminWelcomeTourSteps() {
  return [
    routeContentStep(
      "dashboard",
      "admin-menu-admin-dashboard",
      '[data-tour-target="admin-dashboard"]',
      "Admin Dashboard",
      "This page summarizes health, worker status, release information, and scheduled task counts.",
    ),
    sidebarStep(
      "menu-osint-source",
      "admin-menu-osint-source",
      "OSINT Source",
      "Open the source administration area from here.",
    ),
    routeContentStep(
      "osint-source-table",
      "admin-menu-osint-source",
      osintSourceTableOrDefaultButton,
      "OSINT Source table",
      "This table lists configured feeds and collectors. If no sources exist yet, use the load default sources button to seed the defaults.",
    ),
    sidebarStep(
      "menu-bot",
      "admin-menu-bot",
      "Bot",
      "Open automated processing and analysis bot configuration.",
    ),
    routeContentStep(
      "bot-table",
      "admin-menu-bot",
      tableElement("bot-table"),
      "Bot table",
      "This table lists the automated processing steps that can run after collection.",
    ),
    sidebarStep(
      "menu-scheduler",
      "admin-menu-scheduler",
      "Scheduler",
      "Open queue, job, and worker scheduling details.",
    ),
    routeContentStep(
      "scheduler-table",
      "admin-menu-scheduler",
      schedulerTableElement,
      "Scheduled jobs",
      "This table shows scheduled jobs and helps you inspect what work is queued to run.",
    ),
    sidebarStep(
      "menu-role",
      "admin-menu-role",
      "Role",
      "Open the permission role configuration area.",
    ),
    routeContentStep(
      "role-table",
      "admin-menu-role",
      tableElement("role-table"),
      "Role table",
      "This table lists permission sets that can be assigned to users.",
    ),
    sidebarStep(
      "menu-user",
      "admin-menu-user",
      "User",
      "Open account and role assignment management.",
    ),
    routeContentStep(
      "user-table",
      "admin-menu-user",
      tableElement("user-table"),
      "User table",
      "This table lists user accounts, assigned roles, and account metadata.",
    ),
    {
      id: "welcome-complete",
      popover: {
        title: "Welcome tour complete",
        description:
          "Complete this tour now, or continue with advanced administration areas.",
      },
    },
  ];
}

function adminAdvancedTourSteps() {
  return [
    sidebarStep(
      "menu-report-item-type",
      "admin-menu-report-item-type",
      "Report Item Type",
      "Open report structure and field configuration.",
    ),
    routeContentStep(
      "report-item-type-table",
      "admin-menu-report-item-type",
      tableElement("report_item_type-table"),
      "Report item type table",
      "This table lists the report structures analysts can use when creating reports.",
    ),
    sidebarStep(
      "menu-template",
      "admin-menu-template",
      "Template",
      "Open presenter template management.",
    ),
    routeContentStep(
      "template-table",
      "admin-menu-template",
      tableElement("template-table"),
      "Template table",
      "This table lists templates used to render reports and products.",
    ),
    sidebarStep(
      "menu-product-type",
      "admin-menu-product-type",
      "Product Type",
      "Open product rendering configuration.",
    ),
    routeContentStep(
      "product-type-table",
      "admin-menu-product-type",
      tableElement("product_type-table"),
      "Product type table",
      "This table lists product rendering definitions and their presenter settings.",
    ),
    sidebarStep(
      "menu-publisher-preset",
      "admin-menu-publisher-preset",
      "Publisher Preset",
      "Open reusable publishing destination settings.",
    ),
    routeContentStep(
      "publisher-preset-table",
      "admin-menu-publisher-preset",
      tableElement("publisher_preset-table"),
      "Publisher preset table",
      "This table lists reusable publishing destinations and parameters.",
    ),
    sidebarStep(
      "menu-word-list",
      "admin-menu-word-list",
      "Word List",
      "Open reusable word list management.",
    ),
    routeContentStep(
      "word-list-table",
      "admin-menu-word-list",
      tableElement("word_list-table"),
      "Word list table",
      "This table lists reusable terms for collection, filtering, tagging, and enrichment.",
    ),
  ];
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

function findStepIndex(steps, stepId) {
  return Math.max(
    0,
    steps.findIndex((step) => step.id === stepId),
  );
}

function getTourSteps(tourName) {
  return tourName === "advanced"
    ? adminAdvancedTourSteps()
    : adminWelcomeTourSteps();
}

function getTourId(root, tourName) {
  return tourName === "advanced"
    ? root.dataset.advancedTourId
    : root.dataset.welcomeTourId;
}

function getCompletionDataKey(tourName) {
  return tourName === "advanced" ? "advancedCompleted" : "welcomeCompleted";
}

function startAdminOnboardingTour(root, tourName, startStepId) {
  if (!root || typeof self.driver !== "function") {
    return;
  }

  const tourId = getTourId(root, tourName);
  const completionDataKey = getCompletionDataKey(tourName);
  const steps = getTourSteps(tourName);
  const startIndex = startStepId ? findStepIndex(steps, startStepId) : 0;
  const startStep = steps[startIndex];

  if (
    !tourId || root.dataset[completionDataKey] === "true" ||
    steps.length === 0
  ) {
    clearResumeState();
    return;
  }

  if (startStep && !isCurrentTourRoute(startStep)) {
    writeResumeState(tourName, tourId, startStep.id);
    navigateToStepRoute(startStep);
    return;
  }

  let persisted = false;
  function markTour(status, options = {}) {
    if (persisted) {
      return;
    }
    persisted = true;
    root.dataset[completionDataKey] = status === "completed" ? "true" : "false";
    clearResumeState();
    void saveOnboardingTour(root, tourId, status, options);
  }

  function closeTour(status, options = {}) {
    markTour(status, options);
    destroyTour();
  }

  let destroyStarted = false;
  function destroyTour() {
    if (destroyStarted) {
      return;
    }
    destroyStarted = true;
    driverObj.destroy();
  }

  function moveToStep(nextIndex, currentElement) {
    const nextStep = steps[nextIndex];
    if (!nextStep) {
      closeTour("completed");
      return;
    }

    if (!isCurrentTourRoute(nextStep)) {
      writeResumeState(tourName, tourId, nextStep.id);
      navigateToStepRoute(nextStep, currentElement);
      return;
    }

    if (nextIndex > driverObj.getActiveIndex()) {
      driverObj.moveNext();
      return;
    }

    driverObj.movePrevious();
  }

  const driverObj = self.driver({
    steps,
    showProgress: true,
    showButtons: ["next", "previous", "close"],
    nextBtnText: "Next",
    prevBtnText: "Back",
    doneBtnText: tourName === "advanced"
      ? "Complete advanced tour"
      : "Complete now",
    overlayOpacity: 0.55,
    overlayClickBehavior: () => closeTour("dismissed"),
    smoothScroll: true,
    stagePadding: 6,
    stageRadius: 4,
    disableActiveInteraction: true,
    onNextClick: (element) => {
      if (driverObj.isLastStep()) {
        closeTour("completed");
        return;
      }
      moveToStep(driverObj.getActiveIndex() + 1, element);
    },
    onPrevClick: (element) => {
      if (!driverObj.hasPreviousStep()) {
        return;
      }
      moveToStep(driverObj.getActiveIndex() - 1, element);
    },
    onCloseClick: () => closeTour("dismissed"),
    onDestroyStarted: () => {
      markTour("dismissed");
      destroyTour();
    },
    onPopoverRender: (popover) => {
      if (tourName === "advanced" || !driverObj.isLastStep()) {
        return;
      }
      const advancedButton = makeAdvancedTourButton(
        root,
        () => {
          closeTour("completed", { continueOnboarding: true });
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

  clearResumeState();
  driverObj.drive(startIndex);
}

function isAutostartRoute(root) {
  if (!root.dataset.autostartRoute) {
    return false;
  }
  const autostartUrl = new URL(root.dataset.autostartRoute, self.location.href);
  return urlsShareRoute(autostartUrl, currentTourUrl());
}

function shouldAutostartTour(root, tourName) {
  return tourName === "advanced" || isAutostartRoute(root);
}

function startAdminTours(root) {
  if (!root || root.dataset.started === "true") {
    return;
  }

  const resumeState = readResumeState();
  if (resumeState?.tourName && resumeState?.stepId) {
    root.dataset.started = "true";
    requestAnimationFrame(() =>
      startAdminOnboardingTour(
        root,
        resumeState.tourName,
        resumeState.stepId,
      )
    );
    return;
  }

  const tourName = root.dataset.welcomeCompleted === "true"
    ? "advanced"
    : "welcome";
  const completionDataKey = getCompletionDataKey(tourName);

  if (
    root.dataset[completionDataKey] === "true" ||
    !shouldAutostartTour(root, tourName)
  ) {
    return;
  }

  root.dataset.started = "true";
  requestAnimationFrame(() => startAdminOnboardingTour(root, tourName));
}

function initAdminOnboarding() {
  startAdminTours(document.getElementById("admin-onboarding-tour"));
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initAdminOnboarding, {
    once: true,
  });
} else {
  initAdminOnboarding();
}

self.TaranisOnboarding = {
  startAdminTours,
  startAdminTour: startAdminOnboardingTour,
};
