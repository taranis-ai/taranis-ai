(function () {
  const pageDataNode = document.getElementById("collaboration-page-data");
  if (!pageDataNode || !window.CollaborationWorkspaceStore) {
    return;
  }

  const pageData = JSON.parse(pageDataNode.textContent || "{}");
  const channelId = pageData.channelId;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const rootPrefix = window.location.pathname.includes("/frontend")
    ? window.location.pathname.split("/frontend", 1)[0]
    : "";
  const socketUrl = `${protocol}//${window.location.host}${rootPrefix}/collaboration/ws?channel_id=${encodeURIComponent(channelId)}&story_id=${encodeURIComponent(pageData.selectedStoryId || "")}`;

  const store = new window.CollaborationWorkspaceStore(pageData);
  const connectionBadge = document.querySelector("[data-collab-connection-status]");
  const saveStatusNode = document.querySelector("[data-collab-save-status]");
  const fieldElements = Array.from(document.querySelectorAll("[data-collab-field]"));
  const lockStatusElements = new Map(
    Array.from(document.querySelectorAll("[data-collab-lock-status]")).map((node) => [node.dataset.collabLockStatus, node]),
  );
  const editorHosts = new Map(
    Array.from(document.querySelectorAll("[data-collab-editor-host]")).map((node) => [node.dataset.collabEditorHost, node]),
  );

  const runtime = {
    socket: null,
    selectionTimer: null,
    fields: new Map(),
  };

  const escapeHtml = (value) => String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

  const selectedStory = () => store.selectedStory();
  const workspace = () => store.workspace();
  const isConnected = () => Boolean(runtime.socket) && runtime.socket.readyState === WebSocket.OPEN;

  const setSaveStatus = (text) => {
    if (saveStatusNode) {
      saveStatusNode.textContent = text;
    }
  };

  const setConnectionState = (label, className) => {
    if (!connectionBadge) {
      return;
    }
    connectionBadge.textContent = label;
    connectionBadge.className = className;
  };

  const sendMessage = (type, payload) => {
    if (!isConnected()) {
      return;
    }
    runtime.socket.send(JSON.stringify({ type, channel_id: channelId, payload }));
  };

  const syncEditorSelections = () => {
    runtime.fields.forEach((field) => field.syncRemoteSelections());
  };

  const storyPresenceLabel = (fieldName) => {
    if (!isConnected()) {
      return "Disconnected";
    }
    const viewers = store.remoteSelectionsFor(store.state.selectedStoryId, fieldName);
    if (!viewers.length) {
      return "Nobody here";
    }
    if (viewers.length === 1) {
      return `${viewers[0].username} is here`;
    }
    return `${viewers.length} editing`;
  };

  const renderFieldPresenceLabels = () => {
    store.TEXT_FIELDS.forEach((fieldName) => {
      const statusNode = lockStatusElements.get(fieldName);
      if (statusNode) {
        statusNode.textContent = storyPresenceLabel(fieldName);
      }
    });
  };

  const anyEditorHasFocus = () => Array.from(runtime.fields.values()).some((field) => field.hasFocus());

  const syncEditorStory = ({ force = false } = {}) => {
    runtime.fields.forEach((field) => field.sync({ force, connected: isConnected() }));
    syncEditorSelections();
  };

  const clearSelectionForField = (fieldName, snapshotId = store.state.selectedStoryId) => {
    if (!fieldName || !snapshotId) {
      return;
    }
    sendMessage("collab.story.selection.clear", {
      snapshot_id: snapshotId,
      field_name: fieldName,
      selected_story_id: snapshotId,
    });
  };

  const clearActiveSelection = () => {
    if (!store.state.activeField || !store.state.selectedStoryId) {
      return;
    }
    clearSelectionForField(store.state.activeField, store.state.selectedStoryId);
    store.clearActiveField();
    syncEditorSelections();
    renderFieldPresenceLabels();
  };

  const sendSelectionUpdate = () => {
    if (!store.state.activeField || !store.state.selectedStoryId) {
      return;
    }
    const field = runtime.fields.get(store.state.activeField);
    if (!field) {
      return;
    }
    const selection = field.getSelection();
    sendMessage("collab.story.selection.update", {
      snapshot_id: store.state.selectedStoryId,
      field_name: store.state.activeField,
      anchor: selection.anchor,
      head: selection.head,
      selected_story_id: store.state.selectedStoryId,
    });
  };

  const scheduleSelectionUpdate = () => {
    if (runtime.selectionTimer) {
      window.clearTimeout(runtime.selectionTimer);
    }
    runtime.selectionTimer = window.setTimeout(sendSelectionUpdate, 70);
  };

  const formatTimestamp = (value) => {
    if (!value) {
      return "";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return "";
    }
    return date.toLocaleString();
  };

  const instanceShortName = (item) => item?.participant_short_name || (item?.participant_base_url ? "remote" : "");
  const instanceLabel = (item) => {
    const person = item?.author || item?.owner || item?.actor || "system";
    const shortName = instanceShortName(item);
    return shortName ? `${person} (${shortName})` : person;
  };
  const instanceTitle = (item) => item?.participant_base_url || "";
  const shortNameFromBaseUrl = (baseUrl) => {
    if (!baseUrl) {
      return "";
    }
    try {
      const hostname = new URL(baseUrl).hostname || "";
      return hostname.split(".", 1)[0] || hostname;
    } catch {
      return "";
    }
  };
  const currentPresence = () => store.state.channel.presence?.find((entry) => entry.session_id === store.state.sessionId) || null;

  const chatBubbleStyle = (item) => {
    const hue = window.CollabEditor?.selectionColor
      ? window.CollabEditor.selectionColor(item?.participant_base_url || item?.author || "")
      : 210;
    return `border-color:hsl(${hue} 55% 72%);background:linear-gradient(180deg,hsl(${hue} 70% 96%),hsl(${hue} 60% 92%));`;
  };

  const renderStoryButtons = () => {
    document.querySelectorAll("[data-collab-focus-story]").forEach((button) => {
      const storyId = button.dataset.collabFocusStory;
      const active = storyId === store.state.selectedStoryId;
      button.classList.toggle("border-primary", active);
      button.classList.toggle("bg-primary/6", active);
    });
    (store.state.channel.stories || []).forEach((story) => {
      const titleNode = document.querySelector(`[data-collab-story-title="${CSS.escape(story.id)}"]`);
      if (titleNode) {
        titleNode.textContent = story.title || "Untitled Story";
      }
      const summaryNode = document.querySelector(`[data-collab-story-summary="${CSS.escape(story.id)}"]`);
      if (summaryNode) {
        summaryNode.textContent = story.story?.summary || story.description || "";
      }
      const countNode = document.querySelector(`[data-collab-news-count="${CSS.escape(story.id)}"]`);
      if (countNode) {
        countNode.textContent = String((story.story?.news_items || []).length);
      }
    });
  };

  const renderPresence = () => {
    const presenceRoot = document.querySelector("[data-collab-presence-list]");
    if (!presenceRoot) {
      return;
    }
    const livePresence = store.state.channel.presence || [];
    const liveByParticipant = new Map();
    livePresence.forEach((entry) => {
      if (!liveByParticipant.has(entry.participant_base_url)) {
        liveByParticipant.set(entry.participant_base_url, []);
      }
      liveByParticipant.get(entry.participant_base_url).push(entry);
    });

    presenceRoot.innerHTML = (store.state.channel.participants || []).map((participant) => {
      const users = liveByParticipant.get(participant.base_url) || [];
      const liveUsers = users.map((user) => escapeHtml(user.username)).join(", ");
      return `
        <div class="rounded-[1.25rem] border border-base-300 p-3">
          <div class="flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="truncate font-semibold">${escapeHtml(participant.base_url)}</div>
              <div class="mt-1 text-xs text-base-content/60">${escapeHtml(participant.role || "participant")}</div>
            </div>
            <div class="h-2.5 w-2.5 rounded-full ${users.length ? "bg-success" : "bg-base-300"}"></div>
          </div>
          ${users.length ? `<div class="mt-3 text-xs text-base-content/60">Live: ${liveUsers}</div>` : ""}
        </div>
      `;
    }).join("");

    const stack = document.querySelector("[data-collab-participant-stack]");
    if (stack) {
      stack.innerHTML = livePresence.slice(0, 6).map((entry) => `
        <div class="rounded-full border-2 border-base-100">
          <div class="flex h-9 w-9 items-center justify-center rounded-full border border-base-300 bg-base-100 text-xs font-semibold text-base-content">${escapeHtml((entry.username || "?").slice(0, 2).toUpperCase())}</div>
        </div>
      `).join("");
    }
  };

  const renderList = (containerSelector, items, emptyText, formatter) => {
    const roots = Array.from(document.querySelectorAll(containerSelector));
    if (!roots.length) {
      return;
    }
    const markup = items.length
      ? items.map(formatter).join("")
      : `<div class="text-sm text-base-content/55">${escapeHtml(emptyText)}</div>`;
    roots.forEach((root) => {
      root.innerHTML = markup;
    });
  };

  const renderBriefing = () => {
    const story = selectedStory();
    const briefing = workspace().briefing || {};

    document.querySelectorAll("[data-collab-prioritized-title]").forEach((node) => {
      node.textContent = story?.story?.title || story?.title || "Untitled Story";
    });
    document.querySelectorAll("[data-collab-prioritized-description]").forEach((node) => {
      node.textContent = story?.story?.description || story?.description || "";
    });

    renderList("[data-collab-key-takeaways]", briefing.key_takeaways || [], "No takeaways yet.", (item) => `
      <div class="mb-2 flex items-start gap-2 text-sm">
        <span class="mt-1 h-1.5 w-1.5 rounded-full bg-primary"></span>
        <span>${escapeHtml(item)}</span>
      </div>
    `);
    renderList("[data-collab-risks-list]", briefing.risks || [], "No risks captured.", (item) => `
      <div class="mb-2 flex items-start gap-2 text-sm">
        <span class="mt-1 h-1.5 w-1.5 rounded-full bg-error"></span>
        <span>${escapeHtml(item)}</span>
      </div>
    `);
    renderList("[data-collab-questions-list]", briefing.key_questions || [], "No open questions.", (item) => `
      <div class="mb-2 flex items-start gap-2 text-sm">
        <span class="mt-1 h-1.5 w-1.5 rounded-full bg-info"></span>
        <span>${escapeHtml(item)}</span>
      </div>
    `);
    renderList("[data-collab-source-labels]", briefing.source_labels || [], "No source labels.", (item) => `
      <span class="mr-2 inline-flex rounded-full bg-base-200 px-2 py-1 text-xs">${escapeHtml(item)}</span>
    `);

    const impactNode = document.querySelector("[data-collab-impact]");
    if (impactNode) {
      impactNode.innerHTML = briefing.impact
        ? `<span class="inline-flex rounded-full bg-primary/10 px-3 py-1 text-sm font-semibold text-primary">${escapeHtml(briefing.impact)}</span>`
        : `<span class="text-base-content/55">Impact not set.</span>`;
    }

    const relatedStoriesNode = document.querySelector("[data-collab-related-stories]");
    if (relatedStoriesNode) {
      const relatedStories = (briefing.related_story_ids || [])
        .map((storyId) => (store.state.channel.stories || []).find((storyItem) => storyItem.id === storyId))
        .filter(Boolean);
      relatedStoriesNode.innerHTML = relatedStories.length
        ? relatedStories.map((storyItem) => `<div class="mb-2 text-sm font-medium">${escapeHtml(storyItem.title || "Untitled Story")}</div>`).join("")
        : `<div class="text-sm text-base-content/55">No related stories selected.</div>`;
    }

    const evidenceSummaryNode = document.querySelector("[data-collab-evidence-summary]");
    if (evidenceSummaryNode) {
      const newsCount = (story?.story?.news_items || []).length;
      evidenceSummaryNode.innerHTML = newsCount
        ? `<div class="text-sm">${newsCount} evidence item${newsCount === 1 ? "" : "s"} in the selected story.</div>`
        : `<div class="text-sm text-base-content/55">No evidence items yet.</div>`;
    }
  };

  const renderDecisions = () => {
    renderList("[data-collab-decisions-list]", workspace().decisions || [], "No decisions yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-start justify-between gap-2">
          <div>
            <div class="text-sm font-medium">${escapeHtml(item.text)}</div>
            <div class="mt-1 flex items-center gap-2 text-xs text-base-content/55">
              <span>${escapeHtml(item.owner || "unknown")}</span>
              ${item.created_at ? `<span>• ${escapeHtml(formatTimestamp(item.created_at))}</span>` : ""}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn btn-ghost btn-xs" type="button" data-collab-item-toggle="decision" data-collab-item-id="${escapeHtml(item.id)}">${item.status === "done" ? "Reopen" : "Done"}</button>
            <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-item-remove="decision" data-collab-item-id="${escapeHtml(item.id)}">Remove</button>
          </div>
        </div>
      </div>
    `);
  };

  const renderTasks = () => {
    renderList("[data-collab-tasks-list]", workspace().tasks || [], "No tasks yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-start justify-between gap-2">
          <div>
            <div class="text-sm font-medium">${escapeHtml(item.text)}</div>
            <div class="mt-1 flex flex-wrap items-center gap-2 text-xs text-base-content/55">
              <span title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</span>
              ${item.status ? `<span>${escapeHtml(item.status)}</span>` : ""}
              ${item.created_at ? `<span>${escapeHtml(formatTimestamp(item.created_at))}</span>` : ""}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <button class="btn btn-ghost btn-xs" type="button" data-collab-item-toggle="task" data-collab-item-id="${escapeHtml(item.id)}">${item.status === "done" ? "Reopen" : "Done"}</button>
            <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-item-remove="task" data-collab-item-id="${escapeHtml(item.id)}">Remove</button>
          </div>
        </div>
      </div>
    `);
  };

  const renderComments = () => {
    renderList("[data-collab-comments-list]", workspace().comments || [], "No comments yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-center justify-between gap-3">
          <div class="text-xs font-semibold text-primary" title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</div>
          ${item.created_at ? `<div class="text-[11px] text-base-content/55">${escapeHtml(formatTimestamp(item.created_at))}</div>` : ""}
        </div>
        <div class="mt-2 text-sm">${escapeHtml(item.text)}</div>
      </div>
    `);
  };

  const renderChat = () => {
    renderList("[data-collab-chat-list]", workspace().chat_messages || [], "No chat messages yet.", (item) => `
      <div class="rounded-[1rem] border p-3 shadow-sm transition-colors hover:border-primary/40" style="${chatBubbleStyle(item)}">
        <div class="flex items-center justify-between gap-3">
          <div class="text-xs font-semibold text-primary" title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</div>
          ${item.created_at ? `<div class="text-[11px] text-base-content/55">${escapeHtml(formatTimestamp(item.created_at))}</div>` : ""}
        </div>
        <div class="mt-2 text-sm">${escapeHtml(item.text)}</div>
      </div>
    `);
  };

  const renderActivity = () => {
    renderList("[data-collab-activity-list]", workspace().activity_items || [], "No recent activity yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="text-sm font-medium">${escapeHtml(item.text)}</div>
        <div class="mt-1 flex items-center justify-between gap-3 text-xs text-base-content/55">
          <div title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</div>
          ${item.created_at ? `<div>${escapeHtml(formatTimestamp(item.created_at))}</div>` : ""}
        </div>
      </div>
    `);
  };

  const renderTimeline = () => {
    renderList("[data-collab-timeline-list]", workspace().timeline_events || [], "No timeline events yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-sm font-medium">${escapeHtml(item.title)}</div>
            ${item.note ? `<div class="mt-1 text-sm text-base-content/70">${escapeHtml(item.note)}</div>` : ""}
          </div>
          ${item.time_label ? `<div class="text-xs text-base-content/55">${escapeHtml(item.time_label)}</div>` : ""}
        </div>
        <div class="mt-3 flex justify-end">
          <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-item-remove="timeline_event" data-collab-item-id="${escapeHtml(item.id)}">Remove</button>
        </div>
      </div>
    `);
  };

  const renderRoomStory = ({ forceEditorSync = false } = {}) => {
    const story = selectedStory();
    if (!story) {
      return;
    }

    const titleNode = document.querySelector("[data-collab-room-title]");
    if (titleNode) {
      titleNode.textContent = story.story?.title || story.title || "Untitled Story";
    }

    fieldElements.forEach((fieldElement) => {
      fieldElement.disabled = !isConnected();
    });
    renderFieldPresenceLabels();
    syncEditorStory({ force: forceEditorSync });

    const newsRoot = document.querySelector("[data-collab-news-items]");
    if (newsRoot) {
      newsRoot.innerHTML = (story.story?.news_items || []).length
        ? (story.story.news_items || []).map((newsItem) => `
            <article class="rounded-[1.25rem] border border-base-300 bg-base-100/80 p-4">
              <div class="text-sm font-semibold">${escapeHtml(newsItem.title || "Untitled News Item")}</div>
              ${newsItem.link ? `<a class="mt-2 block truncate text-xs text-primary underline" href="${escapeHtml(newsItem.link)}" target="_blank" rel="noreferrer">${escapeHtml(newsItem.link)}</a>` : ""}
              ${newsItem.content ? `<p class="mt-3 line-clamp-6 text-sm text-base-content/70">${escapeHtml(newsItem.content)}</p>` : ""}
              ${(store.state.channel.stories || []).length > 1 ? `
                <div class="mt-4 flex gap-2">
                  <select class="select select-bordered select-sm flex-1" data-collab-move-target="${escapeHtml(newsItem.id)}">
                    ${(store.state.channel.stories || []).filter((candidate) => candidate.id !== store.state.selectedStoryId).map((candidate) => `<option value="${escapeHtml(candidate.id)}">${escapeHtml(candidate.title || "Untitled Story")}</option>`).join("")}
                  </select>
                  <button class="btn btn-outline btn-sm" type="button" data-collab-move-news-item="${escapeHtml(newsItem.id)}">Move</button>
                </div>
              ` : ""}
            </article>
          `).join("")
        : `<div class="rounded-[1.25rem] border border-dashed border-base-300 p-4 text-sm text-base-content/55">No evidence items are attached to this story.</div>`;
    }
  };

  const renderSidebarTabs = () => {
    document.querySelectorAll("[data-collab-sidebar-tab]").forEach((button) => {
      button.classList.toggle("tab-active", button.dataset.collabSidebarTab === store.state.sidebarTab);
    });
    document.querySelectorAll("[data-collab-sidebar-panel]").forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.collabSidebarPanel !== store.state.sidebarTab);
    });
  };

  const render = ({ forceEditorSync = false } = {}) => {
    renderStoryButtons();
    renderPresence();
    renderBriefing();
    renderDecisions();
    renderTasks();
    renderComments();
    renderChat();
    renderActivity();
    renderTimeline();
    renderRoomStory({ forceEditorSync });
    renderSidebarTabs();
  };

  const appendOptimisticActivity = (text) => {
    if (!text) {
      return;
    }
    const presence = currentPresence();
    const workspaceState = workspace();
    const nextItem = {
      id: `optimistic-${Date.now()}`,
      text,
      actor: presence?.username || "current user",
      participant_base_url: presence?.participant_base_url || store.state.channel.active_instance_base_url || "",
      participant_short_name: shortNameFromBaseUrl(
        presence?.participant_base_url || store.state.channel.active_instance_base_url || "",
      ),
      created_at: new Date().toISOString(),
    };
    store.state.channel.workspace = {
      ...workspaceState,
      activity_items: [nextItem, ...(workspaceState.activity_items || [])].slice(0, 20),
    };
    render();
  };

  const workspaceActivityText = (target, action) => {
    if (target === "workspace" && action === "set") {
      return "updated workspace view";
    }
    if (target === "briefing" && action === "set") {
      return "updated briefing";
    }
    if (action === "remove") {
      return `removed ${String(target || "").replaceAll("_", " ")}`;
    }
    if (action === "upsert") {
      return `updated ${String(target || "").replaceAll("_", " ")}`;
    }
    return "";
  };

  const applySnapshot = (channel, sessionId) => {
    store.applySnapshot(channel, { sessionId });
    render({ forceEditorSync: true });
  };

  const applyChannelUpdate = (channel) => {
    store.applyChannelState(channel);
    render();
  };

  const applySelectionEvent = (payload) => {
    store.applySelectionEvent(payload);
    syncEditorSelections();
    renderFieldPresenceLabels();
  };

  const applyStoryOp = (payload) => {
    const field = runtime.fields.get(payload.field_name);
    const effectType = field ? field.applyOp(payload) : "render";
    if (effectType === "render") {
      render();
      return;
    }
    render();
  };

  const sendWorkspacePatch = (target, action, data = {}, itemId = null) => {
    appendOptimisticActivity(workspaceActivityText(target, action));
    sendMessage("collab.workspace.patch", {
      target,
      action,
      item_id: itemId,
      data: { ...data, selected_story_id: store.state.selectedStoryId },
    });
  };

  const mountEditors = () => {
    fieldElements.forEach((fieldElement) => {
      const fieldName = fieldElement.dataset.collabField;
      const host = editorHosts.get(fieldName);
      const field = new window.SharedStoryField({
        fieldName,
        fieldElement,
        host,
        store,
        sendMessage,
        callbacks: {
          onPendingChange(name) {
            setSaveStatus(`Merging ${name}...`);
          },
          onFocus(name) {
            const previousField = store.state.activeField;
            if (previousField && previousField !== name) {
              clearSelectionForField(previousField, store.state.selectedStoryId);
            }
            store.setActiveField(name);
            syncEditorSelections();
            renderFieldPresenceLabels();
            scheduleSelectionUpdate();
          },
          onBlur(name) {
            if (store.state.activeField === name && !anyEditorHasFocus()) {
              clearActiveSelection();
              setSaveStatus("Live merge idle.");
            }
          },
          onSelectionChange(name) {
            if (store.state.activeField === name) {
              scheduleSelectionUpdate();
            }
          },
        },
      });
      if (field.mount()) {
        runtime.fields.set(fieldName, field);
      }
    });
  };

  const copyToClipboard = async (text) => {
    if (!text) {
      return false;
    }
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    const tempInput = document.createElement("textarea");
    tempInput.value = text;
    tempInput.setAttribute("readonly", "");
    tempInput.className = "fixed left-[-9999px] top-0";
    document.body.appendChild(tempInput);
    tempInput.select();
    tempInput.setSelectionRange(0, text.length);
    const copied = document.execCommand("copy");
    document.body.removeChild(tempInput);
    return copied;
  };

  const connect = () => {
    runtime.socket = new WebSocket(socketUrl);
    setConnectionState("Connecting...", "rounded-box border border-base-300 bg-base-100 px-4 py-2 text-sm font-medium text-base-content");
    runtime.socket.addEventListener("open", () => {
      setConnectionState("Live", "rounded-box border border-success/30 bg-success/10 px-4 py-2 text-sm font-medium text-success");
      setSaveStatus("Live merge connected.");
      syncEditorStory();
    });
    runtime.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "collab.error") {
        setConnectionState("Sync error", "rounded-box border border-error/30 bg-error/10 px-4 py-2 text-sm font-medium text-error");
        setSaveStatus(message.payload?.message || "Collaboration update failed.");
        syncEditorStory();
        return;
      }
      if (message.type === "collab.state.snapshot") {
        applySnapshot(message.payload.channel, message.payload.session_id);
        setSaveStatus("Live merge connected.");
        return;
      }
      if (message.type === "collab.state.updated") {
        applyChannelUpdate(message.payload.channel);
        setSaveStatus("All changes merged.");
        return;
      }
      if (message.type === "collab.story.ops.applied") {
        applyStoryOp(message.payload);
        setSaveStatus(message.payload.session_id === store.state.sessionId ? "Change merged." : "Remote change merged.");
        return;
      }
      if (message.type === "collab.story.selection.update" || message.type === "collab.story.selection.clear") {
        applySelectionEvent(message.payload);
      }
    });
    runtime.socket.addEventListener("close", () => {
      setConnectionState("Disconnected", "rounded-box border border-error/30 bg-error/10 px-4 py-2 text-sm font-medium text-error");
      setSaveStatus("Live merge disconnected. Reload to reconnect.");
      syncEditorStory();
    });
  };

  document.addEventListener("click", (event) => {
    const copyButton = event.target.closest("[data-collab-copy-link]");
    if (copyButton) {
      const link = copyButton.dataset.collabCopyLink;
      copyToClipboard(link)
        .then((copied) => {
          if (copied) {
            setSaveStatus("Invite link copied.");
            return;
          }
          window.prompt("Copy this invite link:", link);
          setSaveStatus("Invite link ready to copy.");
        })
        .catch(() => {
          window.prompt("Copy this invite link:", link);
          setSaveStatus("Invite link ready to copy.");
        });
      return;
    }

    const sidebarTabButton = event.target.closest("[data-collab-sidebar-tab]");
    if (sidebarTabButton) {
      store.setSidebarTab(sidebarTabButton.dataset.collabSidebarTab || "collaboration");
      renderSidebarTabs();
      return;
    }

    const storyButton = event.target.closest("[data-collab-focus-story]");
    if (storyButton) {
      clearActiveSelection();
      store.switchStory(storyButton.dataset.collabFocusStory);
      sendWorkspacePatch("workspace", "set", { focused_story_id: store.state.selectedStoryId });
      render({ forceEditorSync: true });
      return;
    }

    const removeButton = event.target.closest("[data-collab-item-remove]");
    if (removeButton) {
      sendWorkspacePatch(removeButton.dataset.collabItemRemove, "remove", {}, removeButton.dataset.collabItemId);
      return;
    }

    const toggleButton = event.target.closest("[data-collab-item-toggle]");
    if (toggleButton) {
      const target = toggleButton.dataset.collabItemToggle;
      const itemId = toggleButton.dataset.collabItemId;
      const items = workspace()[target === "decision" ? "decisions" : "tasks"] || [];
      const item = items.find((entry) => entry.id === itemId);
      if (!item) {
        return;
      }
      const nextStatus = item.status === "done" ? (target === "task" ? "todo" : "open") : "done";
      sendWorkspacePatch(target, "upsert", { ...item, status: nextStatus }, itemId);
      return;
    }

    const moveButton = event.target.closest("[data-collab-move-news-item]");
    if (moveButton) {
      const newsItemId = moveButton.dataset.collabMoveNewsItem;
      const select = document.querySelector(`[data-collab-move-target="${CSS.escape(newsItemId)}"]`);
      if (!select?.value) {
        return;
      }
      setSaveStatus("Moving news item...");
      sendMessage("collab.news_item.move", {
        source_snapshot_id: store.state.selectedStoryId,
        target_snapshot_id: select.value,
        news_item_id: newsItemId,
        selected_story_id: store.state.selectedStoryId,
      });
    }
  });

  document.addEventListener("submit", (event) => {
    const entryForm = event.target.closest("[data-collab-entry-form]");
    if (entryForm) {
      event.preventDefault();
      const target = entryForm.dataset.target;
      const formData = new FormData(entryForm);
      const data = Object.fromEntries(formData.entries());
      const presence = currentPresence();
      const currentUser = presence?.username || "current user";
      const currentBaseUrl = presence?.participant_base_url || store.state.channel.active_instance_base_url || "";
      sendWorkspacePatch(target, "upsert", {
        ...data,
        text: data.text || data.title || "",
        author: currentUser,
        owner: currentUser,
        participant_base_url: currentBaseUrl,
      });
      entryForm.reset();
      return;
    }

    const briefingListForm = event.target.closest("[data-collab-briefing-list-form]");
    if (briefingListForm) {
      event.preventDefault();
      const field = briefingListForm.dataset.field;
      const value = (new FormData(briefingListForm).get("value") || "").toString().trim();
      if (!value) {
        return;
      }
      const currentValues = [...(workspace().briefing?.[field] || [])];
      currentValues.unshift(value);
      sendWorkspacePatch("briefing", "set", { [field]: currentValues });
      briefingListForm.reset();
      return;
    }

    const briefingSetForm = event.target.closest("[data-collab-briefing-set-form]");
    if (briefingSetForm) {
      event.preventDefault();
      const field = briefingSetForm.dataset.field;
      const value = (new FormData(briefingSetForm).get("value") || "").toString().trim();
      sendWorkspacePatch("briefing", "set", { [field]: value || null });
      briefingSetForm.reset();
    }
  });

  window.addEventListener("beforeunload", () => {
    clearActiveSelection();
    if (runtime.selectionTimer) {
      window.clearTimeout(runtime.selectionTimer);
    }
    if (runtime.socket) {
      runtime.socket.close();
    }
  }, { once: true });

  mountEditors();
  render({ forceEditorSync: true });
  connect();
}());
