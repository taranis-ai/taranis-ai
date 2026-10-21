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
    highlightSearch() {
      if (typeof highlightSearchTerm !== "function") return;
      highlightSearchTerm({
        search: root.dataset.highlight === "true" ? root.dataset.search : "",
        selector: "#assess .highlight",
      });
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

function assessSelection() {
  return {
    selectedItems: [],
    storyIds: [],
    firstStoryIndex: 0,
    storyImportantMap: {},
    storyReadMap: {},
    pruneToVisibleOnNextInit: false,
    showHints: false,
    init() {
      this.firstStoryIndex = Number(this.$el.dataset.pageStart || 0);
      this.restoreSelection();
      this.refreshStoryMeta();
      this.pruneSelectionToVisible();
      this.$nextTick(() => this.syncSelectedCardState());
      this.$watch("selectedItems", () => {
        this.persistSelection();
        this.syncSelectedCardState();
      });
    },
    selectionKey() {
      return this.$root.dataset.selectionKey || "";
    },
    restoreSelection() {
      const state = window.assessSelectionState || {};
      if (state.key !== this.selectionKey()) {
        window.assessSelectionState = {
          key: this.selectionKey(),
          selectedItems: [],
          storyImportantMap: {},
          storyReadMap: {},
        };
        return;
      }
      this.selectedItems = Array.isArray(state.selectedItems)
        ? [...new Set(state.selectedItems)]
        : [];
      this.storyImportantMap = state.storyImportantMap || {};
      this.storyReadMap = state.storyReadMap || {};
      this.pruneToVisibleOnNextInit = state.pruneToVisibleOnNextInit === true;
    },
    persistSelection() {
      window.assessSelectionState = {
        key: this.selectionKey(),
        selectedItems: [...new Set(this.selectedItems)],
        storyImportantMap: this.storyImportantMap,
        storyReadMap: this.storyReadMap,
        pruneToVisibleOnNextInit: this.pruneToVisibleOnNextInit,
      };
    },
    pruneSelectionToVisible() {
      if (!this.pruneToVisibleOnNextInit) return;
      const visibleIds = new Set(this.storyIds);
      this.selectedItems = this.selectedItems.filter((id) =>
        visibleIds.has(id)
      );
      this.pruneToVisibleOnNextInit = false;
      this.persistSelection();
    },
    syncSelectedCardState() {
      const storyList = this.$refs.storyList ||
        document.querySelector("#story-list");
      syncSelectedStoryCardState(storyList, this.selectedItems);
    },
    toggleSelection(id) {
      if (this.selectedItems.includes(id)) {
        this.selectedItems = this.selectedItems.filter((item) => item !== id);
      } else {
        this.selectedItems = [...this.selectedItems, id];
      }
    },
    isSelected(id) {
      return this.selectedItems.includes(id);
    },
    clearSelection() {
      this.selectedItems = [];
    },
    refreshStoryMeta() {
      const storyList = this.$refs.storyList ||
        document.querySelector("#story-list");
      if (!storyList) {
        this.storyIds = [];
        this.storyImportantMap = {};
        this.storyReadMap = {};
        return;
      }
      const cards = Array.from(
        storyList.querySelectorAll("article[data-story-id]"),
      );
      const ids = cards
        .map((node) => node.dataset.storyId)
        .filter(Boolean);
      const importantMap = {};
      const readMap = {};
      cards.forEach((node) => {
        const id = node.dataset.storyId;
        if (!id) return;
        importantMap[id] = node.dataset.storyImportant === "true";
        readMap[id] = node.dataset.storyRead === "true";
      });
      this.storyIds = Array.from(new Set(ids));
      this.storyImportantMap = { ...this.storyImportantMap, ...importantMap };
      this.storyReadMap = { ...this.storyReadMap, ...readMap };
      this.persistSelection();
      this.syncSelectedCardState();
    },
    selectAll() {
      this.refreshStoryMeta();
      if (!this.storyIds.length) {
        this.selectedItems = [];
        return;
      }
      this.selectedItems = [...this.storyIds];
    },
    selectedItemsAreImportant() {
      return this.selectedItems.length > 0 &&
        this.selectedItems.every((id) => this.storyImportantMap[id] === true);
    },
    selectedItemsAreRead() {
      return this.selectedItems.length > 0 &&
        this.selectedItems.every((id) => this.storyReadMap[id] === true);
    },
    action_vals(action, value) {
      if (!action && !value) {
        return JSON.stringify({ story_ids: this.selectedItems });
      }
      return JSON.stringify({
        story_ids: this.selectedItems,
        action: action,
        value: value,
      });
    },
    openStoryEdit() {
      if (this.selectedItems.length !== 1) return;
      const storyId = this.selectedItems[0];
      const storyEditTemplate = this.$el.dataset.editUrl;
      const url = new URL(
        storyEditTemplate.replace("__ID__", storyId),
        window.location.origin,
      );
      url.searchParams.set(
        "assess_url",
        document.getElementById("assess").dataset.assessUrl,
      );
      window.location.href = url;
    },
  };
}
