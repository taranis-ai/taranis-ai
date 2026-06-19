(function () {
  class CollaborationWorkspaceStore {
    constructor(pageData) {
      this.TEXT_FIELDS = ["title", "description", "summary", "comments"];
      this.state = {
        mode: pageData.mode || "overview",
        channel: pageData.channel || {},
        sessionId: null,
        selectedStoryId: pageData.selectedStoryId || ((pageData.channel?.workspace || {}).focused_story_id || ""),
        sidebarTab: "collaboration",
        activeField: null,
        opCounter: 0,
      };
      this.applyChannelState(this.state.channel);
    }

    selectedStory() {
      return (this.state.channel.stories || []).find((story) => story.id === this.state.selectedStoryId) || null;
    }

    workspace() {
      return this.state.channel.workspace || {
        briefing: { key_takeaways: [], risks: [], key_questions: [], source_labels: [], related_story_ids: [] },
        decisions: [],
        tasks: [],
        comments: [],
        chat_messages: [],
        timeline_events: [],
        activity_items: [],
      };
    }

    sharedDocFor(snapshotId, fieldName) {
      return (this.state.channel.shared_docs || []).find(
        (item) => item.snapshot_id === snapshotId && item.field_name === fieldName,
      ) || null;
    }

    remoteSelectionsFor(snapshotId, fieldName) {
      return (this.state.channel.text_selections || []).filter(
        (item) => item.snapshot_id === snapshotId && item.field_name === fieldName && item.session_id !== this.state.sessionId,
      );
    }

    applySnapshot(channel, { sessionId } = {}) {
      if (sessionId) {
        this.state.sessionId = sessionId;
      }
      this.applyChannelState(channel);
    }

    applyChannelState(channel) {
      this.state.channel = channel || {};
      const focusedStoryId = this.state.channel.workspace?.focused_story_id;
      if (
        !this.state.selectedStoryId
        || !(this.state.channel.stories || []).some((story) => story.id === this.state.selectedStoryId)
      ) {
        this.state.selectedStoryId = focusedStoryId || this.state.channel.stories?.[0]?.id || "";
      }
    }

    switchStory(storyId) {
      this.state.selectedStoryId = storyId || "";
    }

    setSidebarTab(tabName) {
      this.state.sidebarTab = tabName || "collaboration";
    }

    setActiveField(fieldName) {
      this.state.activeField = fieldName;
    }

    clearActiveField() {
      this.state.activeField = null;
    }

    nextOpId(fieldName) {
      this.state.opCounter += 1;
      return `${this.state.sessionId || "pending"}-${fieldName}-${this.state.opCounter}`;
    }

    applySelectionEvent(payload) {
      if (payload.channel) {
        this.applyChannelState(payload.channel);
      }
    }

    applyStoryOp(payload, fieldState) {
      if (payload.channel) {
        this.applyChannelState(payload.channel);
      }
      if (!fieldState || fieldState.snapshotId !== payload.snapshot_id) {
        return { type: "render" };
      }

      fieldState.version = Number(payload.version || fieldState.version);
      if (payload.session_id === this.state.sessionId) {
        fieldState.pendingOps = fieldState.pendingOps.filter((item) => item.opId !== payload.op_id);
        return { type: "ack" };
      }

      const rebasedUpdates = (fieldState.pendingOps || []).reduce(
        (changes, pendingOp) => this.transformChanges(changes, pendingOp.changes),
        payload.updates || [],
      );
      return { type: "remote", changes: rebasedUpdates };
    }

    mapPositionThroughChange(position, change, assoc) {
      const start = Number(change.from || 0);
      const end = Number(change.to ?? start);
      const insertLength = String(change.insert || "").length;
      const delta = insertLength - (end - start);
      if (position < start) return position;
      if (position > end) return position + delta;
      if (position === start && position === end) return assoc > 0 ? position + insertLength : position;
      if (position === start) return assoc < 0 ? start : start + insertLength;
      if (position === end) return assoc < 0 ? start : start + insertLength;
      return assoc < 0 ? start : start + insertLength;
    }

    transformChanges(changes, appliedChanges) {
      return changes.map((change) => {
        let next = { ...change };
        (appliedChanges || []).forEach((appliedChange) => {
          const collapsed = next.from === next.to;
          next = {
            from: this.mapPositionThroughChange(next.from, appliedChange, -1),
            to: this.mapPositionThroughChange(next.to, appliedChange, collapsed ? -1 : 1),
            insert: next.insert,
          };
        });
        return next;
      });
    }
  }

  class SharedStoryField {
    constructor({ fieldName, fieldElement, host, store, sendMessage, callbacks }) {
      this.fieldName = fieldName;
      this.fieldElement = fieldElement;
      this.host = host;
      this.store = store;
      this.sendMessage = sendMessage;
      this.callbacks = callbacks;
      this.binding = null;
      this.snapshotId = "";
      this.version = 0;
      this.pendingOps = [];
    }

    mount() {
      if (!window.CollabEditor) {
        return false;
      }
      this.binding = window.CollabEditor.mountShared({
        textarea: this.fieldElement,
        parent: this.host,
        options: {
          minHeight: this.fieldName === "title" ? "4.25rem" : "8rem",
        },
        onChange: ({ changes }) => {
          if (!this.snapshotId || !changes.length) {
            return;
          }
          const opId = this.store.nextOpId(this.fieldName);
          this.pendingOps.push({ opId, changes });
          this.callbacks.onPendingChange(this.fieldName);
          this.sendMessage("collab.story.ops.submit", {
            snapshot_id: this.snapshotId,
            field_name: this.fieldName,
            version: this.version + this.pendingOps.length - 1,
            op_id: opId,
            updates: changes,
            selected_story_id: this.snapshotId,
          });
        },
        onFocus: () => this.callbacks.onFocus(this.fieldName),
        onBlur: () => this.callbacks.onBlur(this.fieldName),
        onSelectionChange: () => this.callbacks.onSelectionChange(this.fieldName),
      });
      this.snapshotId = this.store.state.selectedStoryId;
      this.version = Number(this.store.sharedDocFor(this.snapshotId, this.fieldName)?.version || 0);
      return true;
    }

    sync({ force = false, connected = false } = {}) {
      if (!this.binding) {
        return;
      }
      const selectedStoryId = this.store.state.selectedStoryId;
      const doc = this.store.sharedDocFor(selectedStoryId, this.fieldName) || {
        text: this.store.selectedStory()?.story?.[this.fieldName] || "",
        version: 0,
      };
      const switchedStory = this.snapshotId !== selectedStoryId;
      if (switchedStory || force) {
        this.binding.setText(doc.text || "");
        this.snapshotId = selectedStoryId;
        this.version = Number(doc.version || 0);
        this.pendingOps = [];
      } else if (!this.pendingOps.length && this.version !== Number(doc.version || 0)) {
        this.binding.setText(doc.text || "");
        this.version = Number(doc.version || 0);
      }
      this.binding.setEditable(Boolean(connected));
    }

    applyOp(payload) {
      if (!this.binding) {
        return "render";
      }
      const effect = this.store.applyStoryOp(payload, this);
      if (effect.type === "remote") {
        this.binding.applyRemoteChanges(effect.changes);
      }
      return effect.type;
    }

    syncRemoteSelections() {
      if (!this.binding) {
        return;
      }
      const selections = this.store.state.activeField === this.fieldName
        ? this.store.remoteSelectionsFor(this.store.state.selectedStoryId, this.fieldName)
        : [];
      this.binding.setRemoteSelections(selections);
    }

    hasFocus() {
      return this.binding ? this.binding.hasFocus() : false;
    }

    getSelection() {
      return this.binding ? this.binding.getSelection() : { anchor: 0, head: 0 };
    }
  }

  window.CollaborationWorkspaceStore = CollaborationWorkspaceStore;
  window.SharedStoryField = SharedStoryField;
}());
