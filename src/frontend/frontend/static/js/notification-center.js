(function () {
  const STORAGE_KEY = "taranis.sessionNotifications";
  const MAX_NOTIFICATIONS = 100;

  function read() {
    try {
      const notifications = JSON.parse(
        self.sessionStorage.getItem(STORAGE_KEY) || "[]",
      );
      return Array.isArray(notifications) ? notifications : [];
    } catch {
      return [];
    }
  }

  function write(notifications) {
    try {
      self.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(notifications));
    } catch {}
  }

  function add({ message, level = "info" }) {
    const trimmedMessage = typeof message === "string" ? message.trim() : "";
    if (!trimmedMessage) return;
    const storedLevel = ["error", "info", "success", "warning"].includes(level)
      ? level
      : "info";

    write([
      {
        message: trimmedMessage,
        level: storedLevel,
        createdAt: new Date().toISOString(),
      },
      ...read(),
    ].slice(0, MAX_NOTIFICATIONS));
  }

  function clear() {
    try {
      self.sessionStorage.removeItem(STORAGE_KEY);
    } catch {}
  }

  self.taranisNotifications = { add, clear, read };
})();
