(function () {
  const STORAGE_KEY = "taranis.sessionNotifications";
  const MAX_NOTIFICATIONS = 100;

  function readNotifications() {
    try {
      const notifications = JSON.parse(
        self.sessionStorage.getItem(STORAGE_KEY) || "[]",
      );
      return Array.isArray(notifications) ? notifications : [];
    } catch {
      return [];
    }
  }

  function writeNotifications(notifications) {
    try {
      self.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
    } catch {}
  }

  function notificationLevel(alert) {
    if (alert.classList.contains("alert-error")) return "error";
    if (alert.classList.contains("alert-warning")) return "warning";
    if (alert.classList.contains("alert-success")) return "success";
    return "info";
  }

  function renderNotificationCenter() {
    const list = document.querySelector("[data-notification-center-list]");
    if (!list) return;

    const notifications = readNotifications();
    list.replaceChildren();
    if (!notifications.length) {
      const empty = document.createElement("p");
      empty.className = "py-8 text-center text-base-content/60";
      empty.textContent = list.dataset.emptyMessage || "";
      list.append(empty);
      return;
    }

    notifications.forEach((notification) => {
      const item = document.createElement("article");
      item.className = `alert alert-${
        notification.level || "info"
      } flex items-start justify-between gap-4`;

      const message = document.createElement("span");
      message.className = "whitespace-pre-wrap";
      message.textContent = notification.message;
      item.append(message);

      const timestamp = document.createElement("time");
      timestamp.className = "shrink-0 text-xs opacity-70";
      timestamp.dateTime = notification.createdAt;
      timestamp.textContent = new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short",
      }).format(new Date(notification.createdAt));
      item.append(timestamp);
      list.append(item);
    });
  }

  function addNotification({ message, level = "info" }) {
    const trimmedMessage = typeof message === "string" ? message.trim() : "";
    if (!trimmedMessage) return;

    const notifications = readNotifications();
    notifications.unshift({
      message: trimmedMessage,
      level,
      createdAt: new Date().toISOString(),
    });
    writeNotifications(notifications.slice(0, MAX_NOTIFICATIONS));
    document.dispatchEvent(new CustomEvent("notification-center:added"));
  }

  function recordAlerts(container) {
    container.querySelectorAll(".alert").forEach((alert) => {
      if (alert.dataset.notificationCenterRecorded === "true") return;
      const message =
        alert.querySelector("#notification-message")?.textContent ||
        alert.textContent;
      alert.dataset.notificationCenterRecorded = "true";
      addNotification({ message, level: notificationLevel(alert) });
    });
  }

  function observeNotificationBar() {
    const notificationBar = document.getElementById("notification-bar");
    if (!notificationBar) return;
    recordAlerts(notificationBar);

    new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof Element)) return;
          if (node.id === "notification-bar") recordAlerts(node);
          node.querySelectorAll?.("#notification-bar").forEach(recordAlerts);
          if (node.matches(".alert")) recordAlerts(node.parentElement || node);
        });
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  document.addEventListener(
    "notification-center:added",
    renderNotificationCenter,
  );
  document.addEventListener("DOMContentLoaded", () => {
    observeNotificationBar();
    renderNotificationCenter();
  });
  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) return;
    if (event.target.closest("[data-notification-center-clear]")) {
      try {
        self.sessionStorage.removeItem(STORAGE_KEY);
      } catch {}
      renderNotificationCenter();
    }
    if (event.target.closest("[data-session-notifications-clear-on-logout]")) {
      try {
        self.sessionStorage.removeItem(STORAGE_KEY);
      } catch {}
    }
  });

  self.taranisNotifications = { add: addNotification };
})();
