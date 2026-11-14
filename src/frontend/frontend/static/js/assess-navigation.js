const ASSESS_DAY_MS = 86_400_000;

// Mirrors models.assess.assess_range_bounds: UTC start and exclusive calendar end (null when rolling) in epoch ms.
function assessRangeBounds(range, nowMs) {
  const now = new Date(nowMs);
  const midnight = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  if (range === "24h") return [nowMs - ASSESS_DAY_MS, null];
  if (/^last\d+$/.test(range)) return [nowMs - Number(range.slice(4)) * ASSESS_DAY_MS, null];
  if (range === "day") return [midnight - ASSESS_DAY_MS, null];
  if (range === "week") {
    const start = midnight - ((now.getUTCDay() + 6) % 7) * ASSESS_DAY_MS;
    return [start, start + 7 * ASSESS_DAY_MS];
  }
  if (range === "month") {
    return [Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), 1), Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + 1, 1)];
  }
  return [midnight, midnight + ASSESS_DAY_MS];
}

// Datetime-local min/max (UTC clock, second precision) that keep From inside a preset; empty without a preset.
function assessTimeFromBounds(range, nowMs) {
  if (!range) return {};
  const [start, end] = assessRangeBounds(range, nowMs);
  const format = (ms) => new Date(ms).toISOString().slice(0, 19);
  return { min: format(Math.ceil(start / 1000) * 1000), max: end === null ? "" : format(end - 1000) };
}

function assessTimeFilters() {
  return {
    timeClearPending: false,
    timeFromNotice: "",
    serverClockOffset: 0,
    init() {
      const renderedAt = Number(this.$el.dataset.now);
      if (renderedAt) this.serverClockOffset = renderedAt - Date.now();
    },
    applyTimeFromBounds() {
      const input = this.$refs.timeFrom;
      const bounds = assessTimeFromBounds(this.$refs.timePreset.value, Date.now() + this.serverClockOffset);
      for (const attribute of ["min", "max"]) {
        if (bounds[attribute]) input.setAttribute(attribute, bounds[attribute]);
        else input.removeAttribute(attribute);
      }
      this.checkTimeFrom();
    },
    checkTimeFrom() {
      const input = this.$refs.timeFrom;
      if (!input.value) return false;
      const outside = input.validity.rangeUnderflow || input.validity.rangeOverflow;
      this.timeFromNotice = outside
        ? "From was cleared because it is outside the selected time period."
        : "";
      if (outside) {
        input.value = "";
        input.removeAttribute("name");
      }
      return outside;
    },
    clearTimeFilters() {
      this.timeClearPending = true;
      for (const input of [this.$refs.timeFrom, this.$refs.timeTo]) {
        input.value = "";
        input.removeAttribute("name");
      }
      this.$refs.timePreset.value = "";
      this.timeFromNotice = "";
      this.applyTimeFromBounds();
    },
    restoreTimeFilters() {
      if (!this.timeClearPending) return;
      const params = new URL(window.location.href).searchParams;
      for (const [ref, name] of [["timeFrom", "timefrom"], ["timeTo", "timeto"]]) {
        const input = this.$refs[ref];
        input.value = params.get(name) || "";
        input.name = input.value ? name : "";
      }
      this.$refs.timePreset.value = params.get("range") || "";
      this.$refs.customPeriod.selected = !this.$refs.timePreset.value &&
        !!(this.$refs.timeFrom.value || this.$refs.timeTo.value);
      this.applyTimeFromBounds();
      this.timeClearPending = false;
    },
  };
}

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
  let root;
  return {
    selectedItems: [],
    storyIds: [],
    firstStoryIndex: 0,
    storyImportantMap: {},
    storyReadMap: {},
    pruneToVisibleOnNextInit: false,
    showHints: false,
    init() {
      root = this.$el;
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
      const storyEditTemplate = root.dataset.editUrl;
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
