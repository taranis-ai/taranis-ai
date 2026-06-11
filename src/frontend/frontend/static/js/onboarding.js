const onboardingResumeKey = "taranis.onboarding.resume";
const onboardingTriggerKey = "taranis.onboarding.trigger";
const onboardingStatusCompleted = "completed";
const onboardingScopeGlobal = "global";
const onboardingScopeUser = "user";
const adminWelcomeTourId = "admin_welcome_v1";
const adminAdvancedTourId = "admin_advanced_v1";
const userProductOverviewTaskId = "user_product_overview_v1";
const taskDefinitions = {};

function getOnboardingCSRFToken() {
  return document.cookie
    .split("; ")
    .find((row) => row.startsWith("csrf_access_token="))
    ?.split("=")[1];
}

function registerOnboardingTask(definition) {
  taskDefinitions[definition.id] = definition;
}

function parseDatasetJson(root, key, fallback) {
  try {
    return JSON.parse(root.dataset[key] || "");
  } catch {
    return fallback;
  }
}

function readPendingTasks(root) {
  return parseDatasetJson(root, "pendingTasks", []).filter(
    (task) => task?.id && task?.scope,
  );
}

function writePendingTasks(root, tasks) {
  root.dataset.pendingTasks = JSON.stringify(tasks);
}

function isTaskPending(root, taskId, scope) {
  return readPendingTasks(root).some(
    (task) => task.id === taskId && (!scope || task.scope === scope),
  );
}

function removePendingTask(root, taskId, scope) {
  writePendingTasks(
    root,
    readPendingTasks(root).filter(
      (task) => task.id !== taskId || (scope && task.scope !== scope),
    ),
  );
}

function readUserPermissions(root) {
  return new Set(parseDatasetJson(root, "userPermissions", []));
}

function hasAnyPermission(root, permissions) {
  if (!permissions?.length) {
    return true;
  }
  const userPermissions = readUserPermissions(root);
  return (
    userPermissions.has("ALL") ||
    permissions.some((permission) => userPermissions.has(permission))
  );
}

function buildOnboardingFormData(task, status) {
  const formData = new FormData();
  formData.set(`onboarding_tasks[${task.id}]`, status);
  return formData;
}

function saveOnboardingTask(root, task, status) {
  const action = root.dataset.profileAction;
  if (!action) {
    return Promise.resolve();
  }

  const body = buildOnboardingFormData(task, status);
  return fetch(action, {
    method: "POST",
    body,
    credentials: "same-origin",
    headers: {
      "HX-Request": "true",
      "X-CSRF-TOKEN": getOnboardingCSRFToken() || "",
    },
  }).catch((error) => {
    console.error("Failed to save onboarding task state", error);
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
    return JSON.parse(self.sessionStorage.getItem(onboardingResumeKey));
  } catch {
    return null;
  }
}

function writeResumeState(taskId, stepId) {
  try {
    self.sessionStorage.setItem(
      onboardingResumeKey,
      JSON.stringify({ taskId, stepId }),
    );
  } catch {
    // Storage can be unavailable in restricted browser modes. The tour still works on the current page.
  }
}

function clearResumeState() {
  try {
    self.sessionStorage.removeItem(onboardingResumeKey);
  } catch {
    // Ignore storage failures.
  }
}

function readTriggerState() {
  try {
    return JSON.parse(self.sessionStorage.getItem(onboardingTriggerKey));
  } catch {
    return null;
  }
}

function writeTriggerState(taskId) {
  try {
    self.sessionStorage.setItem(
      onboardingTriggerKey,
      JSON.stringify({ taskId }),
    );
  } catch {
    // Storage can be unavailable in restricted browser modes. The click still navigates normally.
  }
}

function clearTriggerState() {
  try {
    self.sessionStorage.removeItem(onboardingTriggerKey);
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

function sidebarStep(id, target, title, description, requiredPermissions) {
  return {
    id,
    requiredPermissions,
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
  requiredPermissions,
) {
  return {
    id,
    requiredPermissions,
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

function userProductOverviewSteps() {
  return [
    routeContentStep(
      "assess-nav",
      "nav-assess",
      '[data-tour-target="nav-assess"]',
      "Assess",
      "Assess is where you review incoming stories, filter the stream, and decide what needs follow-up.",
      ["ASSESS_ACCESS"],
    ),
    routeContentStep(
      "assess-page",
      "nav-assess",
      '[data-tour-target="assess-page"]',
      "Story review",
      "This workspace lists stories and news items so you can compare source material before escalating it.",
      ["ASSESS_ACCESS"],
    ),
    routeContentStep(
      "assess-filters",
      "nav-assess",
      '[data-tour-target="assess-filters"]',
      "Assess filters",
      "Use filters to narrow the story stream. Save as default stores the view you want to start from next time.",
      ["ASSESS_ACCESS"],
    ),
    routeContentStep(
      "analyze-nav",
      "nav-analyze",
      '[data-tour-target="nav-analyze"]',
      "Analyze",
      "Analyze turns assessed stories into structured reports for review and publication.",
      ["ANALYZE_ACCESS"],
    ),
    routeContentStep(
      "analyze-page",
      "nav-analyze",
      '[data-tour-target="analyze-page"]',
      "Reports",
      "Reports collect relevant stories and analysis fields into one reusable work product.",
      ["ANALYZE_ACCESS"],
    ),
    routeContentStep(
      "publish-nav",
      "nav-publish",
      '[data-tour-target="nav-publish"]',
      "Publish",
      "Publish converts reports into configured products and sends them to selected destinations.",
      ["PUBLISH_ACCESS"],
    ),
    routeContentStep(
      "publish-page",
      "nav-publish",
      '[data-tour-target="publish-page"]',
      "Products",
      "Products are rendered outputs. Render first, then publish manually or through a configured preset.",
      ["PUBLISH_ACCESS"],
    ),
  ];
}

function findStepIndex(steps, stepId) {
  return Math.max(
    0,
    steps.findIndex((step) => step.id === stepId),
  );
}

function taskById(taskId) {
  const definition = taskDefinitions[taskId];
  return definition ? { id: taskId, scope: definition.scope } : null;
}

function getTaskSteps(root, taskId) {
  const definition = taskDefinitions[taskId];
  if (!definition) {
    return [];
  }
  return definition.steps().filter((step) =>
    hasAnyPermission(root, step.requiredPermissions)
  );
}

function makeAdvancedTourButton(root) {
  if (!isTaskPending(root, adminAdvancedTourId, onboardingScopeGlobal)) {
    return null;
  }

  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-outline btn-sm";
  button.textContent = "Advanced tour";
  button.dataset.testid = "admin-onboarding-advanced-tour";
  button.addEventListener("click", () => {
    closeActiveTour(root, adminWelcomeTourId, onboardingStatusCompleted);
    setTimeout(() => startOnboardingTask(root, adminAdvancedTourId), 150);
  });
  return button;
}

function pendingAdminTaskId(root) {
  if (isTaskPending(root, adminWelcomeTourId, onboardingScopeGlobal)) {
    return adminWelcomeTourId;
  }
  return isTaskPending(root, adminAdvancedTourId, onboardingScopeGlobal)
    ? adminAdvancedTourId
    : null;
}

function matchesAnySelector(element, selectors) {
  return selectors.some((selector) => element?.closest?.(selector));
}

function installOnboardingClickTriggers(root) {
  if (!root || root.dataset.triggersInstalled === "true") {
    return;
  }
  root.dataset.triggersInstalled = "true";

  document.addEventListener("click", (event) => {
    const link = getTourLink(event.target);
    if (!link) {
      return;
    }

    const triggeredTaskId = matchesAnySelector(link, [
        '[data-tour-target="nav-admin"]',
        '[data-tour-target="admin-menu-admin-dashboard"]',
      ])
      ? pendingAdminTaskId(root)
      : matchesAnySelector(link, ['[data-tour-target="nav-assess"]'])
      ? (isTaskPending(root, userProductOverviewTaskId, onboardingScopeUser)
        ? userProductOverviewTaskId
        : null)
      : null;

    if (triggeredTaskId) {
      writeTriggerState(triggeredTaskId);
    }
  });
}

let activeCloseTour = null;

function closeActiveTour(root, taskId, status) {
  if (typeof activeCloseTour === "function") {
    activeCloseTour(status);
    return;
  }

  const task = taskById(taskId);
  if (!task) {
    return;
  }
  removePendingTask(root, task.id, task.scope);
  clearResumeState();
  void saveOnboardingTask(root, task, status);
}

function startOnboardingTask(root, taskId, startStepId) {
  if (!root || typeof self.driver !== "function") {
    return;
  }

  const definition = taskDefinitions[taskId];
  const task = taskById(taskId);
  const steps = getTaskSteps(root, taskId);
  const startIndex = startStepId ? findStepIndex(steps, startStepId) : 0;
  const startStep = steps[startIndex];

  if (
    !definition ||
    !task ||
    !isTaskPending(root, task.id, task.scope) ||
    steps.length === 0
  ) {
    clearResumeState();
    return;
  }

  if (startStep && !isCurrentTourRoute(startStep)) {
    writeResumeState(task.id, startStep.id);
    navigateToStepRoute(startStep);
    return;
  }

  let persisted = false;
  function markTask(status) {
    if (persisted) {
      return;
    }
    persisted = true;
    removePendingTask(root, task.id, task.scope);
    clearResumeState();
    void saveOnboardingTask(root, task, status);
  }

  function closeTour(status) {
    markTask(status);
    destroyTour();
  }
  activeCloseTour = closeTour;

  let destroyStarted = false;
  let routeChangeInProgress = false;
  function destroyTour() {
    if (destroyStarted) {
      return;
    }
    destroyStarted = true;
    activeCloseTour = null;
    driverObj.destroy();
  }

  function moveToStep(nextIndex, currentElement) {
    const nextStep = steps[nextIndex];
    if (!nextStep) {
      closeTour(onboardingStatusCompleted);
      return;
    }

    if (!isCurrentTourRoute(nextStep)) {
      writeResumeState(task.id, nextStep.id);
      routeChangeInProgress = true;
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
    doneBtnText: definition.doneBtnText,
    overlayOpacity: 0.55,
    overlayClickBehavior: () => closeTour("dismissed"),
    smoothScroll: true,
    stagePadding: 6,
    stageRadius: 4,
    disableActiveInteraction: true,
    onNextClick: (element) => {
      if (driverObj.isLastStep()) {
        closeTour(onboardingStatusCompleted);
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
      if (routeChangeInProgress) {
        activeCloseTour = null;
        return;
      }
      markTask("dismissed");
      destroyTour();
    },
    onPopoverRender: (popover) => {
      if (task.id !== adminWelcomeTourId || !driverObj.isLastStep()) {
        return;
      }
      const advancedButton = makeAdvancedTourButton(root);
      if (advancedButton) {
        popover.footerButtons.insertBefore(advancedButton, popover.nextButton);
      }
    },
  });

  clearResumeState();
  driverObj.drive(startIndex);
}

function startOnboarding(root) {
  if (!root || root.dataset.started === "true") {
    return;
  }
  installOnboardingClickTriggers(root);

  const resumeState = readResumeState();
  if (resumeState?.taskId && resumeState?.stepId) {
    root.dataset.started = "true";
    requestAnimationFrame(() =>
      startOnboardingTask(root, resumeState.taskId, resumeState.stepId)
    );
    return;
  }

  const triggerState = readTriggerState();
  const task = triggerState?.taskId ? taskById(triggerState.taskId) : null;
  clearTriggerState();
  if (!task || !isTaskPending(root, task.id, task.scope)) {
    return;
  }

  root.dataset.started = "true";
  requestAnimationFrame(() => startOnboardingTask(root, task.id));
}

function startAdminTours(root) {
  if (!root) {
    return;
  }
  const taskId = isTaskPending(root, adminWelcomeTourId, onboardingScopeGlobal)
    ? adminWelcomeTourId
    : adminAdvancedTourId;
  startOnboardingTask(root, taskId);
}

function initOnboarding() {
  startOnboarding(
    document.getElementById("onboarding-root") ||
      document.getElementById("admin-onboarding-tour"),
  );
}

registerOnboardingTask({
  id: adminWelcomeTourId,
  scope: onboardingScopeGlobal,
  steps: adminWelcomeTourSteps,
  doneBtnText: "Complete now",
});

registerOnboardingTask({
  id: adminAdvancedTourId,
  scope: onboardingScopeGlobal,
  steps: adminAdvancedTourSteps,
  doneBtnText: "Complete advanced tour",
});

registerOnboardingTask({
  id: userProductOverviewTaskId,
  scope: onboardingScopeUser,
  steps: userProductOverviewSteps,
  doneBtnText: "Finish overview",
});

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initOnboarding, {
    once: true,
  });
} else {
  initOnboarding();
}

self.TaranisOnboarding = {
  start: startOnboarding,
  startTask: startOnboardingTask,
  startAdminTours,
  startAdminTour(root, tourName, startStepId) {
    const taskId = tourName === "advanced"
      ? adminAdvancedTourId
      : adminWelcomeTourId;
    startOnboardingTask(root, taskId, startStepId);
  },
};
