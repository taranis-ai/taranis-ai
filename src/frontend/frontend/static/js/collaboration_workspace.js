(function () {
  const pageDataNode = document.getElementById("collaboration-page-data");
  if (!pageDataNode) {
    return;
  }

  const pageData = JSON.parse(pageDataNode.textContent || "{}");
  const channelId = pageData.channelId;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const rootPrefix = window.location.pathname.includes("/frontend")
    ? window.location.pathname.split("/frontend", 1)[0]
    : "";
  const socketUrl = `${protocol}//${window.location.host}${rootPrefix}/collaboration/ws?channel_id=${encodeURIComponent(channelId)}&story_id=${encodeURIComponent(pageData.selectedStoryId || "")}`;

  const connectionBadge = document.querySelector("[data-collab-connection-status]");
  const saveStatusNode = document.querySelector("[data-collab-save-status]");
  const fieldElements = Array.from(document.querySelectorAll("[data-collab-field]"));
  const lockStatusElements = new Map(
    Array.from(document.querySelectorAll("[data-collab-lock-status]")).map((node) => [node.dataset.collabLockStatus, node]),
  );

  const state = {
    mode: pageData.mode || "overview",
    channel: pageData.channel || {},
    socket: null,
    sessionId: null,
    selectedStoryId: pageData.selectedStoryId || ((pageData.channel?.workspace || {}).focused_story_id || ""),
    sidebarTab: "collaboration",
    patchTimers: new Map(),
    heartbeatTimers: new Map(),
  };

  const escapeHtml = (value) => String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");

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

  const selectedStory = () => (state.channel.stories || []).find((story) => story.id === state.selectedStoryId) || null;

  const workspace = () => state.channel.workspace || {
    briefing: { key_takeaways: [], risks: [], key_questions: [], source_labels: [], related_story_ids: [] },
    decisions: [],
    tasks: [],
    comments: [],
    chat_messages: [],
    timeline_events: [],
    activity_items: [],
  };

  const storyLockFor = (fieldName) => (state.channel.locks || []).find(
    (item) => item.snapshot_id === state.selectedStoryId && item.field_name === fieldName,
  );

  const sendMessage = (type, payload) => {
    if (!state.socket || state.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    state.socket.send(JSON.stringify({ type, channel_id: channelId, payload }));
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

  const renderStoryButtons = () => {
    document.querySelectorAll("[data-collab-focus-story]").forEach((button) => {
      const storyId = button.dataset.collabFocusStory;
      const active = storyId === state.selectedStoryId;
      button.classList.toggle("border-primary", active);
      button.classList.toggle("bg-primary/6", active);
    });
    (state.channel.stories || []).forEach((story) => {
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
    const livePresence = state.channel.presence || [];
    const liveByParticipant = new Map();
    livePresence.forEach((entry) => {
      if (!liveByParticipant.has(entry.participant_base_url)) {
        liveByParticipant.set(entry.participant_base_url, []);
      }
      liveByParticipant.get(entry.participant_base_url).push(entry);
    });

    presenceRoot.innerHTML = (state.channel.participants || []).map((participant) => {
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
    const root = document.querySelector(containerSelector);
    if (!root) {
      return;
    }
    if (!items.length) {
      root.innerHTML = `<div class="text-sm text-base-content/55">${escapeHtml(emptyText)}</div>`;
      return;
    }
    root.innerHTML = items.map(formatter).join("");
  };

  const renderBriefing = () => {
    const story = selectedStory();
    const currentWorkspace = workspace();
    const briefing = currentWorkspace.briefing || {};

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
        .map((storyId) => (state.channel.stories || []).find((story) => story.id === storyId))
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
            <div class="mt-1 text-xs text-base-content/55">${escapeHtml(item.owner || "unknown")}</div>
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
            <div class="mt-1 text-xs text-base-content/55">${escapeHtml(item.owner || "")} ${item.status ? `• ${escapeHtml(item.status)}` : ""}</div>
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
        <div class="text-xs font-semibold text-primary">${escapeHtml(item.author || "unknown")}</div>
        <div class="mt-2 text-sm">${escapeHtml(item.text)}</div>
      </div>
    `);
  };

  const renderChat = () => {
    renderList("[data-collab-chat-list]", workspace().chat_messages || [], "No chat messages yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 bg-primary/5 p-3">
        <div class="text-xs font-semibold text-primary">${escapeHtml(item.author || "unknown")}</div>
        <div class="mt-2 text-sm">${escapeHtml(item.text)}</div>
      </div>
    `);
  };

  const renderActivity = () => {
    renderList("[data-collab-activity-list]", workspace().activity_items || [], "No recent activity yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="text-sm font-medium">${escapeHtml(item.text)}</div>
        <div class="mt-1 text-xs text-base-content/55">${escapeHtml(item.actor || "system")}</div>
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

  const renderRoomStory = () => {
    const story = selectedStory();
    if (!story) {
      return;
    }

    const titleNode = document.querySelector("[data-collab-room-title]");
    if (titleNode) {
      titleNode.textContent = story.story?.title || story.title || "Untitled Story";
    }

    fieldElements.forEach((fieldElement) => {
      const fieldName = fieldElement.dataset.collabField;
      const value = story.story?.[fieldName] || "";
      const lock = storyLockFor(fieldName);
      const ownedBySelf = lock && lock.session_id === state.sessionId;
      if (document.activeElement !== fieldElement || !ownedBySelf) {
        fieldElement.value = value;
      }
      fieldElement.disabled = !state.socket || state.socket.readyState !== WebSocket.OPEN || (lock && !ownedBySelf);
      const lockNode = lockStatusElements.get(fieldName);
      if (lockNode) {
        lockNode.textContent = !state.socket || state.socket.readyState !== WebSocket.OPEN
          ? "Disconnected"
          : !lock
            ? "Unlocked"
            : ownedBySelf
              ? "Locked by you"
              : `Locked by ${lock.username}`;
      }
    });

    const newsRoot = document.querySelector("[data-collab-news-items]");
    if (newsRoot) {
      newsRoot.innerHTML = (story.story?.news_items || []).length
        ? (story.story.news_items || []).map((newsItem) => `
            <article class="rounded-[1.25rem] border border-base-300 bg-base-100/80 p-4">
              <div class="text-sm font-semibold">${escapeHtml(newsItem.title || "Untitled News Item")}</div>
              ${newsItem.link ? `<a class="mt-2 block truncate text-xs text-primary underline" href="${escapeHtml(newsItem.link)}" target="_blank" rel="noreferrer">${escapeHtml(newsItem.link)}</a>` : ""}
              ${newsItem.content ? `<p class="mt-3 line-clamp-6 text-sm text-base-content/70">${escapeHtml(newsItem.content)}</p>` : ""}
              ${(state.channel.stories || []).length > 1 ? `
                <div class="mt-4 flex gap-2">
                  <select class="select select-bordered select-sm flex-1" data-collab-move-target="${escapeHtml(newsItem.id)}">
                    ${(state.channel.stories || []).filter((candidate) => candidate.id !== state.selectedStoryId).map((candidate) => `<option value="${escapeHtml(candidate.id)}">${escapeHtml(candidate.title || "Untitled Story")}</option>`).join("")}
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
      const isActive = button.dataset.collabSidebarTab === state.sidebarTab;
      button.classList.toggle("tab-active", isActive);
    });
    document.querySelectorAll("[data-collab-sidebar-panel]").forEach((panel) => {
      panel.classList.toggle("hidden", panel.dataset.collabSidebarPanel !== state.sidebarTab);
    });
  };

  const render = () => {
    renderStoryButtons();
    renderPresence();
    renderBriefing();
    renderDecisions();
    renderTasks();
    renderComments();
    renderChat();
    renderActivity();
    renderTimeline();
    renderRoomStory();
    renderSidebarTabs();
  };

  const applyChannel = (channel, { sessionId } = {}) => {
    state.channel = channel;
    if (sessionId) {
      state.sessionId = sessionId;
    }
    const focusedStoryId = channel.workspace?.focused_story_id;
    if (!state.selectedStoryId || !(channel.stories || []).some((story) => story.id === state.selectedStoryId)) {
      state.selectedStoryId = focusedStoryId || channel.stories?.[0]?.id || "";
    }
    render();
  };

  const schedulePatch = (fieldName, value) => {
    const currentTimer = state.patchTimers.get(fieldName);
    if (currentTimer) {
      window.clearTimeout(currentTimer);
    }
    setSaveStatus(`Syncing ${fieldName}...`);
    state.patchTimers.set(fieldName, window.setTimeout(() => {
      sendMessage("collab.story.patch", {
        snapshot_id: state.selectedStoryId,
        fields: { [fieldName]: value },
        selected_story_id: state.selectedStoryId,
      });
    }, 180));
  };

  const startHeartbeat = (fieldName) => {
    const currentTimer = state.heartbeatTimers.get(fieldName);
    if (currentTimer) {
      window.clearInterval(currentTimer);
    }
    state.heartbeatTimers.set(fieldName, window.setInterval(() => {
      sendMessage("collab.lock.heartbeat", {
        snapshot_id: state.selectedStoryId,
        field_name: fieldName,
        selected_story_id: state.selectedStoryId,
      });
    }, 4000));
  };

  const stopHeartbeat = (fieldName) => {
    const currentTimer = state.heartbeatTimers.get(fieldName);
    if (currentTimer) {
      window.clearInterval(currentTimer);
      state.heartbeatTimers.delete(fieldName);
    }
  };

  const sendWorkspacePatch = (target, action, data = {}, itemId = null) => {
    sendMessage("collab.workspace.patch", {
      target,
      action,
      item_id: itemId,
      data: { ...data, selected_story_id: state.selectedStoryId },
    });
  };

  const connect = () => {
    state.socket = new WebSocket(socketUrl);
    setConnectionState("Connecting...", "rounded-box border border-base-300 bg-base-100 px-4 py-2 text-sm font-medium text-base-content");
    state.socket.addEventListener("open", () => {
      setConnectionState("Live", "rounded-box border border-success/30 bg-success/10 px-4 py-2 text-sm font-medium text-success");
      setSaveStatus("Live sync connected.");
    });
    state.socket.addEventListener("message", (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "collab.error") {
        setConnectionState("Sync error", "rounded-box border border-error/30 bg-error/10 px-4 py-2 text-sm font-medium text-error");
        setSaveStatus(message.payload?.message || "Collaboration update failed.");
        fieldElements.forEach((fieldElement) => {
          fieldElement.disabled = true;
        });
        return;
      }
      if (message.type === "collab.state.snapshot") {
        applyChannel(message.payload.channel, { sessionId: message.payload.session_id });
        setSaveStatus("Live sync connected.");
        return;
      }
      if (message.type === "collab.state.updated") {
        applyChannel(message.payload.channel);
        setSaveStatus("All changes synced.");
      }
    });
    state.socket.addEventListener("close", () => {
      setConnectionState("Disconnected", "rounded-box border border-error/30 bg-error/10 px-4 py-2 text-sm font-medium text-error");
      setSaveStatus("Live sync disconnected. Reload to reconnect.");
      fieldElements.forEach((fieldElement) => {
        fieldElement.disabled = true;
      });
    });
  };

  fieldElements.forEach((fieldElement) => {
    const fieldName = fieldElement.dataset.collabField;
    fieldElement.addEventListener("focus", () => {
      sendMessage("collab.lock.acquire", {
        snapshot_id: state.selectedStoryId,
        field_name: fieldName,
        selected_story_id: state.selectedStoryId,
      });
      startHeartbeat(fieldName);
    });
    fieldElement.addEventListener("blur", () => {
      stopHeartbeat(fieldName);
      sendMessage("collab.lock.release", {
        snapshot_id: state.selectedStoryId,
        field_name: fieldName,
        selected_story_id: state.selectedStoryId,
      });
      setSaveStatus("Live sync idle.");
    });
    fieldElement.addEventListener("input", () => {
      schedulePatch(fieldName, fieldElement.value);
    });
  });

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
      state.sidebarTab = sidebarTabButton.dataset.collabSidebarTab || "collaboration";
      renderSidebarTabs();
      return;
    }

    const storyButton = event.target.closest("[data-collab-focus-story]");
    if (storyButton) {
      const storyId = storyButton.dataset.collabFocusStory;
      state.selectedStoryId = storyId;
      sendWorkspacePatch("workspace", "set", {
        focused_story_id: storyId,
      });
      render();
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
        source_snapshot_id: state.selectedStoryId,
        target_snapshot_id: select.value,
        news_item_id: newsItemId,
        selected_story_id: state.selectedStoryId,
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
      const payload = {
        ...data,
        text: data.text || data.title || "",
        author: state.channel.presence?.find((entry) => entry.session_id === state.sessionId)?.username || "current user",
        owner: state.channel.presence?.find((entry) => entry.session_id === state.sessionId)?.username || "current user",
      };
      sendWorkspacePatch(target, "upsert", payload);
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
    fieldElements.forEach((fieldElement) => stopHeartbeat(fieldElement.dataset.collabField));
    if (state.socket) {
      state.socket.close();
    }
  }, { once: true });

  render();
  connect();
}());
