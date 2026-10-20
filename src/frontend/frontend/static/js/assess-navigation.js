function assessSearchState() {
  let root;
  return {
    previousSearch: "",
    init() {
      root = this.$el;
      const { assessUrl, offerRestore } = this.$el.dataset;
      try {
        const previous = this.validSearch(
          localStorage.getItem(this.storageKey()),
        );
        if (offerRestore === "true" && previous && previous !== assessUrl) {
          this.previousSearch = previous;
        } else {
          this.saveSearch(assessUrl);
        }
      } catch {
        // Browser storage is optional; native return links still work.
      }
    },
    storageKey() {
      return `taranis.assess.lastSearch:${root.dataset.userId}:${root.dataset.assessPath}`;
    },
    validSearch(value) {
      if (!value || !value.startsWith("/")) return "";
      const url = new URL(value, window.location.origin);
      if (
        url.origin !== window.location.origin ||
        url.pathname !== root.dataset.assessPath ||
        !url.search || url.searchParams.has("reset")
      ) return "";
      return url.pathname + url.search;
    },
    saveSearch(value) {
      if (this.previousSearch && value === root.dataset.assessUrl) return;
      this.previousSearch = "";
      root.dataset.assessUrl = value;
      try {
        const search = this.validSearch(value);
        if (search) {
          localStorage.setItem(this.storageKey(), search);
        } else {
          localStorage.removeItem(this.storageKey());
        }
      } catch {
        // Storage may be disabled or full.
      }
    },
    dismiss() {
      this.previousSearch = "";
      this.saveSearch(root.dataset.assessUrl);
    },
  };
}
