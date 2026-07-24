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
  let resyncTimer;

  function scheduleResync(reason) {
    self.clearTimeout(resyncTimer);
    resyncTimer = self.setTimeout(() => {
      document.dispatchEvent(
        new CustomEvent("realtime:resync", { detail: { reason } }),
      );
    }, 300);
  }

  function handleMessage(message) {
    let event;
    try {
      event = JSON.parse(message.data)?.pub?.data;
    } catch {
      return;
    }

    if (!event || event.v !== 1 || typeof event.type !== "string") {
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
  }

  function close() {
    self.clearTimeout(resyncTimer);
    disconnected = opened;
    eventSource?.close();
    eventSource = undefined;
  }

  function connect() {
    if (
      document.body.dataset.realtimeEnabled !== "true" ||
      eventSource ||
      typeof EventSource === "undefined"
    ) {
      return;
    }

    eventSource = new EventSource(document.body.dataset.realtimeUrl);
    eventSource.addEventListener("message", handleMessage);
    eventSource.addEventListener("open", () => {
      if (opened && disconnected) {
        scheduleResync("reconnected");
      }
      opened = true;
      disconnected = false;
    });
    eventSource.addEventListener("error", () => {
      disconnected = true;
    });
  }

  document.addEventListener("click", (event) => {
    if (event.target instanceof Element && event.target.closest("[data-realtime-close-on-logout]")) {
      close();
    }
  });
  self.addEventListener("pagehide", close);
  self.addEventListener("pageshow", connect);

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", connect, { once: true });
  } else {
    connect();
  }
})();
