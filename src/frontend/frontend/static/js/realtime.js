(function () {
  const SUPPORTED_TYPES = new Set([
    "assess.changed",
    "report.item.changed",
    "report.lock.changed",
    "product.rendered",
  ]);

  let eventSource;
  let opened = false;
  let disconnected = false;
  let reconnectAllowed = true;
  let reconnectTimer;
  let resyncTimer;
  let outageTimer;
  let outageNotified = false;

  const PAGE_TARGETS = {
    "assess.changed": "#assess",
    "report.item.changed": "#report",
    "report.lock.changed": "#report",
    "product.rendered": "#publish, #product",
  };

  function scheduleResync(reason) {
    self.clearTimeout(resyncTimer);
    resyncTimer = self.setTimeout(() => {
      document.dispatchEvent(
        new CustomEvent("realtime:resync", { detail: { reason } }),
      );
    }, 300);
  }

  function handleMessage(message) {
    let payload;
    try {
      payload = JSON.parse(message.data);
    } catch {
      return;
    }

    const disconnectCode = payload?.disconnect?.code;
    if (
      Number.isInteger(disconnectCode) && disconnectCode >= 4500 &&
      disconnectCode < 5000
    ) {
      close(true);
      return;
    }

    const event = payload?.pub?.data;
    if (!event) {
      return;
    }
    if (event.v !== 1 || typeof event.type !== "string") {
      scheduleResync("unsupported-event");
      return;
    }
    if (!SUPPORTED_TYPES.has(event.type)) {
      console.warn("Ignoring unknown realtime event type", event.type);
      return;
    }

    document.dispatchEvent(
      new CustomEvent(`realtime:${event.type}`, { detail: event }),
    );
    showDataNotification(event.type);
  }

  function hideStatusNotification() {
    document.getElementById("realtime-status-notification")?.classList.add(
      "hidden",
    );
  }

  function showStatusNotification() {
    outageTimer = undefined;
    outageNotified = true;
    document.getElementById("realtime-status-notification")?.classList.remove(
      "hidden",
    );
  }

  function scheduleOutageNotification() {
    if (outageTimer || outageNotified) {
      return;
    }
    outageTimer = self.setTimeout(showStatusNotification, 15000);
  }

  function hideDataNotification() {
    document.getElementById("realtime-data-notification")?.classList.add(
      "hidden",
    );
  }

  function showDataNotification(eventType) {
    const target = PAGE_TARGETS[eventType];
    const notice = document.getElementById("realtime-data-notification");
    const targetElement = target && document.querySelector(target);
    if (!notice || !targetElement) {
      return;
    }

    const assessEvent = eventType === "assess.changed";
    notice.dataset.refreshTarget = `#${targetElement.id}`;
    notice.querySelector("[data-realtime-data-message]").textContent =
      assessEvent
        ? notice.dataset.assessMessage
        : notice.dataset.defaultMessage;
    const refresh = notice.querySelector("[data-realtime-refresh]");
    refresh.textContent = assessEvent
      ? notice.dataset.assessAction
      : notice.dataset.defaultAction;
    refresh.href = `${self.location.pathname}${self.location.search}`;
    notice.classList.remove("hidden");
  }

  function scheduleReconnect() {
    self.clearTimeout(reconnectTimer);
    reconnectTimer = self.setTimeout(connect, 1000 + Math.random() * 4000);
  }

  function close(permanent = false) {
    reconnectAllowed = permanent ? false : reconnectAllowed;
    self.clearTimeout(reconnectTimer);
    self.clearTimeout(resyncTimer);
    self.clearTimeout(outageTimer);
    outageTimer = undefined;
    outageNotified = false;
    hideStatusNotification();
    disconnected = opened;
    eventSource?.close();
    eventSource = undefined;
  }

  function connect() {
    if (
      document.body.dataset.realtimeEnabled !== "true" ||
      !reconnectAllowed ||
      eventSource ||
      typeof EventSource === "undefined"
    ) {
      return;
    }

    eventSource = new EventSource(document.body.dataset.realtimeUrl);
    eventSource.addEventListener("message", handleMessage);
    eventSource.addEventListener("open", () => {
      self.clearTimeout(outageTimer);
      outageTimer = undefined;
      outageNotified = false;
      hideStatusNotification();
      if (opened && disconnected) {
        scheduleResync("reconnected");
      }
      opened = true;
      disconnected = false;
    });
    eventSource.addEventListener("error", () => {
      if (!reconnectAllowed) {
        return;
      }
      disconnected = true;
      eventSource?.close();
      eventSource = undefined;
      scheduleOutageNotification();
      scheduleReconnect();
    });
  }

  document.addEventListener("click", (event) => {
    if (
      event.target instanceof Element &&
      event.target.closest("[data-realtime-close-on-logout]")
    ) {
      close(true);
      return;
    }
    if (
      event.target instanceof Element &&
      event.target.closest("[data-realtime-dismiss-status]")
    ) {
      hideStatusNotification();
      return;
    }
    if (
      event.target instanceof Element &&
      event.target.closest("[data-realtime-dismiss-data]")
    ) {
      hideDataNotification();
      return;
    }
    const refresh = event.target instanceof Element &&
      event.target.closest("[data-realtime-refresh]");
    const notice = document.getElementById("realtime-data-notification");
    if (refresh && notice?.dataset.refreshTarget && self.htmx?.ajax) {
      event.preventDefault();
      Promise.resolve(
        self.htmx.ajax("GET", refresh.href, {
          target: notice.dataset.refreshTarget,
          select: notice.dataset.refreshTarget,
          swap: "outerHTML",
        }),
      ).then(hideDataNotification).catch(() => {});
    }
  });

  document.addEventListener("realtime:resync", () => {
    const eventType = Object.entries(PAGE_TARGETS).find(([, selector]) =>
      document.querySelector(selector)
    )?.[0];
    if (eventType) {
      showDataNotification(eventType);
    }
  });
  self.addEventListener("pagehide", () => close());
  self.addEventListener("pageshow", connect);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connect, { once: true });
  } else {
    connect();
  }
})();
