(function () {
  const pageDataNode = document.getElementById("collaboration-page-data");
  if (!pageDataNode || !window.CollaborationWorkspaceStore) {
    return;
  }

  const pageData = JSON.parse(pageDataNode.textContent || "{}");
  const channelId = pageData.channelId;
  const newsItemUrlTemplate = pageData.newsItemUrlTemplate || "";
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const rootPrefix = window.location.pathname.includes("/frontend")
    ? window.location.pathname.split("/frontend", 1)[0]
    : "";
  const socketUrl = `${protocol}//${window.location.host}${rootPrefix}/collaboration/ws?channel_id=${encodeURIComponent(channelId)}&story_id=${encodeURIComponent(pageData.selectedStoryId || "")}`;

  const store = new window.CollaborationWorkspaceStore(pageData);
  const connectionBadge = document.querySelector("[data-collab-connection-status]");
  const saveStatusNode = document.querySelector("[data-collab-save-status]");
  const fieldElements = Array.from(document.querySelectorAll("[data-collab-field]"));
  const reportFieldElements = Array.from(document.querySelectorAll("[data-collab-report-field]"));
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
    reportHeartbeats: new Map(),
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
  const isReadOnly = () => store.state.channel?.status !== "open";
  const duplicateNewsItems = () => {
    const storiesByNewsItem = new Map();
    (store.state.channel.stories || []).forEach((story) => {
      const seen = new Set();
      (story.story?.news_items || []).forEach((newsItem) => {
        if (!newsItem.id || seen.has(newsItem.id)) {
          return;
        }
        seen.add(newsItem.id);
        storiesByNewsItem.set(newsItem.id, [...(storiesByNewsItem.get(newsItem.id) || []), story]);
      });
    });
    return new Map([...storiesByNewsItem].filter(([, stories]) => stories.length > 1));
  };

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

  const newsItemDetailUrl = (newsItemId) => {
    if (!newsItemUrlTemplate || !newsItemId) {
      return "";
    }
    return newsItemUrlTemplate.replace("__NEWS_ITEM_ID__", encodeURIComponent(newsItemId));
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
    const stories = store.state.channel.stories || [];
    const duplicates = duplicateNewsItems();
    const storyListRoot = document.querySelector("[data-collab-story-list]");
    if (storyListRoot) {
      storyListRoot.innerHTML = stories.map((story) => {
        const active = story.id === store.state.selectedStoryId;
        const duplicateCount = new Set(
          (story.story?.news_items || []).filter((newsItem) => duplicates.has(newsItem.id)).map((newsItem) => newsItem.id),
        ).size;
        return `
          <div class="rounded-[1.25rem] border p-4 transition ${active ? "border-primary bg-primary/6" : "border-base-300 hover:border-primary/40"}">
            <button type="button" class="block w-full text-left" data-collab-focus-story="${escapeHtml(story.id)}">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <div class="truncate font-semibold" data-collab-story-title="${escapeHtml(story.id)}">${escapeHtml(story.title || "Untitled Story")}</div>
                  <div class="mt-1 break-all text-xs text-base-content/60">${escapeHtml(story.source_instance || "")}</div>
                </div>
                <div class="h-2.5 w-2.5 rounded-full ${active ? "bg-success" : "bg-base-300"}"></div>
              </div>
              <div class="mt-3 flex flex-wrap gap-2 text-[11px] text-base-content/60">
                <span class="rounded-full bg-base-200 px-2 py-1"><span data-collab-news-count="${escapeHtml(story.id)}">${escapeHtml(String((story.story?.news_items || []).length))}</span> News Items</span>
                ${duplicateCount ? `<span class="rounded-full bg-warning/20 px-2 py-1 text-warning-content">${duplicateCount} duplicate${duplicateCount === 1 ? "" : "s"}</span>` : ""}
              </div>
              <p class="mt-3 line-clamp-3 break-all text-sm text-base-content/70" data-collab-story-summary="${escapeHtml(story.id)}">${escapeHtml(story.story?.summary || story.description || "")}</p>
            </button>
            ${store.state.channel.status === "open" ? `
              <div class="mt-3 flex justify-end">
                <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-remove-story="${escapeHtml(story.id)}">Remove Story</button>
              </div>
            ` : ""}
          </div>
        `;
      }).join("");
    }

    document.querySelectorAll("[data-collab-channel-story-count], [data-collab-story-queue-count], [data-collab-overview-story-count]").forEach((node) => {
      node.textContent = String(stories.length);
    });
    document.querySelectorAll("[data-collab-channel-participant-count], [data-collab-overview-participant-count]").forEach((node) => {
      node.textContent = String((store.state.channel.participants || []).length);
    });

    const overviewDescriptionNode = document.querySelector("[data-collab-overview-description]");
    if (overviewDescriptionNode) {
      const selected = selectedStory();
      if (store.state.channel.status !== "open") {
        overviewDescriptionNode.textContent = "This channel is archived. The snapshot below reflects its final state when it was closed.";
      } else if (selected && stories.length === 1) {
        overviewDescriptionNode.textContent = `Current focus: ${selected.story?.title || selected.title || "Untitled Story"}.`;
      } else if (selected) {
        overviewDescriptionNode.textContent = `This channel currently groups ${stories.length} stories. The room remains the place for detailed story editing.`;
      } else {
        overviewDescriptionNode.textContent = "This channel has no stories yet. Add stories from Assess to begin live collaboration.";
      }
    }
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

  const renderChannelInfo = () => {
    const channelInfo = workspace().channel_info || {};
    const chatUrl = String(channelInfo.chat_url || "").trim();
    const resourceUrl = String(channelInfo.resource_url || "").trim();
    const notes = String(channelInfo.notes || "").trim();

    document.querySelectorAll("[data-collab-channel-info-chat]").forEach((node) => {
      node.innerHTML = chatUrl
        ? `<a class="link link-primary break-all text-sm" href="${escapeHtml(chatUrl)}" target="_blank" rel="noreferrer">${escapeHtml(chatUrl)}</a>`
        : `<span class="text-sm text-base-content/55">No chat room pinned.</span>`;
    });
    document.querySelectorAll("[data-collab-channel-info-resource]").forEach((node) => {
      node.innerHTML = resourceUrl
        ? `<a class="link link-primary break-all text-sm" href="${escapeHtml(resourceUrl)}" target="_blank" rel="noreferrer">${escapeHtml(resourceUrl)}</a>`
        : `<span class="text-sm text-base-content/55">No shared resource pinned.</span>`;
    });
    document.querySelectorAll("[data-collab-channel-info-notes]").forEach((node) => {
      node.textContent = notes || "No pinned channel notes yet.";
      node.classList.toggle("text-base-content/55", !notes);
    });

    document.querySelectorAll("[data-collab-channel-info-input='chat_url']").forEach((node) => {
      if (document.activeElement !== node) {
        node.value = chatUrl;
      }
    });
    document.querySelectorAll("[data-collab-channel-info-input='resource_url']").forEach((node) => {
      if (document.activeElement !== node) {
        node.value = resourceUrl;
      }
    });
    document.querySelectorAll("[data-collab-channel-info-input='notes']").forEach((node) => {
      if (document.activeElement !== node) {
        node.value = notes;
      }
    });
  };

  const renderDecisions = () => {
    renderList("[data-collab-decisions-list]", workspace().decisions || [], "No decisions yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-start justify-between gap-2">
          <div class="min-w-0">
            <div class="break-all text-sm font-medium">${escapeHtml(item.text)}</div>
            <div class="mt-1 flex flex-wrap items-start gap-x-2 gap-y-1 text-xs text-base-content/55">
              <span class="break-all">${escapeHtml(item.owner || "unknown")}</span>
              ${item.created_at ? `<span class="break-all">• ${escapeHtml(formatTimestamp(item.created_at))}</span>` : ""}
            </div>
          </div>
          ${isReadOnly() ? "" : `
            <div class="flex flex-wrap items-center justify-end gap-2">
              <button class="btn btn-ghost btn-xs" type="button" data-collab-item-toggle="decision" data-collab-item-id="${escapeHtml(item.id)}">${item.status === "done" ? "Reopen" : "Done"}</button>
              <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-item-remove="decision" data-collab-item-id="${escapeHtml(item.id)}">Remove</button>
            </div>
          `}
        </div>
      </div>
    `);
  };

  const renderTasks = () => {
    renderList("[data-collab-tasks-list]", workspace().tasks || [], "No tasks yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex flex-col gap-3">
          <div class="min-w-0">
            <div class="break-all text-sm font-medium">${escapeHtml(item.text)}</div>
            <div class="mt-1 flex flex-wrap items-start gap-x-2 gap-y-1 text-xs text-base-content/55">
              <span class="min-w-0 break-all" title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</span>
              ${item.status ? `<span>${escapeHtml(item.status)}</span>` : ""}
              ${item.created_at ? `<span class="break-all">${escapeHtml(formatTimestamp(item.created_at))}</span>` : ""}
            </div>
          </div>
          ${isReadOnly() ? "" : `
            <div class="flex flex-wrap items-center justify-end gap-2">
              <button class="btn btn-ghost btn-xs" type="button" data-collab-item-toggle="task" data-collab-item-id="${escapeHtml(item.id)}">${item.status === "done" ? "Reopen" : "Done"}</button>
              <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-item-remove="task" data-collab-item-id="${escapeHtml(item.id)}">Remove</button>
            </div>
          `}
        </div>
      </div>
    `);
  };

  const renderComments = () => {
    renderList("[data-collab-comments-list]", workspace().comments || [], "No comments yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0 break-all text-xs font-semibold text-primary" title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</div>
          ${item.created_at ? `<div class="break-all text-[11px] text-base-content/55">${escapeHtml(formatTimestamp(item.created_at))}</div>` : ""}
        </div>
        <div class="mt-2 break-all text-sm">${escapeHtml(item.text)}</div>
      </div>
    `);
  };

  const renderChat = () => {
    renderList("[data-collab-chat-list]", workspace().chat_messages || [], "No chat messages yet.", (item) => `
      <div class="rounded-[1rem] border p-3 shadow-sm transition-colors hover:border-primary/40" style="${chatBubbleStyle(item)}">
        <div class="flex items-center justify-between gap-3">
          <div class="min-w-0 break-all text-xs font-semibold text-primary" title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</div>
          ${item.created_at ? `<div class="break-all text-[11px] text-base-content/55">${escapeHtml(formatTimestamp(item.created_at))}</div>` : ""}
        </div>
        <div class="mt-2 break-all text-sm">${escapeHtml(item.text)}</div>
      </div>
    `);
  };

  const renderActivity = () => {
    renderList("[data-collab-activity-list]", workspace().activity_items || [], "No recent activity yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="break-all text-sm font-medium">${escapeHtml(item.text)}</div>
        <div class="mt-1 flex flex-wrap items-start justify-between gap-3 text-xs text-base-content/55">
          <div class="min-w-0 break-all" title="${escapeHtml(instanceTitle(item))}">${escapeHtml(instanceLabel(item))}</div>
          ${item.created_at ? `<div class="break-all">${escapeHtml(formatTimestamp(item.created_at))}</div>` : ""}
        </div>
      </div>
    `);
  };

  const renderTimeline = () => {
    renderList("[data-collab-timeline-list]", workspace().timeline_events || [], "No timeline events yet.", (item) => `
      <div class="rounded-[1rem] border border-base-300 p-3">
        <div class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <div class="break-all text-sm font-medium">${escapeHtml(item.title)}</div>
            ${item.note ? `<div class="mt-1 break-all text-sm text-base-content/70">${escapeHtml(item.note)}</div>` : ""}
          </div>
          ${item.time_label ? `<div class="break-all text-xs text-base-content/55">${escapeHtml(item.time_label)}</div>` : ""}
        </div>
        ${isReadOnly() ? "" : `
          <div class="mt-3 flex justify-end">
            <button class="btn btn-ghost btn-xs text-error" type="button" data-collab-item-remove="timeline_event" data-collab-item-id="${escapeHtml(item.id)}">Remove</button>
          </div>
        `}
      </div>
    `);
  };

  const renderRoomStory = ({ forceEditorSync = false } = {}) => {
    const story = selectedStory();
    const duplicates = duplicateNewsItems();
    const titleNode = document.querySelector("[data-collab-room-title]");
    const newsRoot = document.querySelector("[data-collab-news-items]");
    if (!story) {
      if (titleNode) {
        titleNode.textContent = "No story selected";
      }
      fieldElements.forEach((fieldElement) => {
        fieldElement.disabled = true;
      });
      runtime.fields.forEach((field) => field.sync({ force: true, connected: false }));
      if (newsRoot) {
        newsRoot.innerHTML = `<div class="rounded-[1.25rem] border border-dashed border-base-300 p-4 text-sm text-base-content/55">No stories remain in this collaboration channel.</div>`;
      }
      return;
    }

    if (titleNode) {
      titleNode.textContent = story.story?.title || story.title || "Untitled Story";
    }

    fieldElements.forEach((fieldElement) => {
      fieldElement.disabled = !isConnected();
    });
    renderFieldPresenceLabels();
    syncEditorStory({ force: forceEditorSync });

    if (newsRoot) {
      newsRoot.innerHTML = (story.story?.news_items || []).length
        ? (story.story.news_items || []).map((newsItem) => {
            const otherStories = (duplicates.get(newsItem.id) || []).filter((candidate) => candidate.id !== story.id);
            return `
            <article class="rounded-[1.25rem] border ${otherStories.length ? "border-warning bg-warning/5" : "border-base-300 bg-base-100/80"} p-4">
              <div class="text-sm font-semibold">${escapeHtml(newsItem.title || "Untitled News Item")}</div>
              ${otherStories.length ? `<div class="mt-2 text-xs font-medium text-warning-content">Also assigned to ${escapeHtml(otherStories.map((candidate) => candidate.title || "Untitled Story").join(", "))}. Remove one assignment before finalizing.</div>` : ""}
              <div class="mt-2 flex flex-wrap gap-2">
                ${newsItem.id ? `<a class="link link-primary text-xs" href="${escapeHtml(newsItemDetailUrl(newsItem.id))}">Open details</a>` : ""}
                ${newsItem.link ? `<a class="link link-primary text-xs" href="${escapeHtml(newsItem.link)}" target="_blank" rel="noreferrer">Open source</a>` : ""}
              </div>
              ${newsItem.link ? `<div class="mt-2 break-all text-xs text-base-content/60">${escapeHtml(newsItem.link)}</div>` : ""}
              ${newsItem.content ? `<p class="mt-3 line-clamp-6 text-sm text-base-content/70">${escapeHtml(newsItem.content)}</p>` : ""}
              ${store.state.channel.status === "open" ? `
                <div class="mt-4 flex flex-wrap gap-2">
                  ${(store.state.channel.stories || []).length > 1 ? `
                    <select class="select select-bordered select-sm flex-1" data-collab-move-target="${escapeHtml(newsItem.id)}">
                      ${(store.state.channel.stories || []).filter((candidate) => candidate.id !== store.state.selectedStoryId).map((candidate) => `<option value="${escapeHtml(candidate.id)}">${escapeHtml(candidate.title || "Untitled Story")}</option>`).join("")}
                    </select>
                    <button class="btn btn-outline btn-sm" type="button" data-collab-move-news-item="${escapeHtml(newsItem.id)}">Move</button>
                  ` : ""}
                  <button class="btn btn-ghost btn-sm text-error" type="button" data-collab-remove-news-item="${escapeHtml(newsItem.id)}">Remove</button>
                </div>
              ` : ""}
            </article>
          `;
          }).join("")
        : `<div class="rounded-[1.25rem] border border-dashed border-base-300 p-4 text-sm text-base-content/55">No evidence items are attached to this story.</div>`;
    }
  };

  const renderDuplicateState = () => {
    const duplicateCount = duplicateNewsItems().size;
    const warning = document.querySelector("[data-collab-duplicate-warning]");
    const warningText = document.querySelector("[data-collab-duplicate-warning-text]");
    warning?.classList.toggle("hidden", duplicateCount === 0);
    if (warningText) {
      warningText.textContent = `${duplicateCount} news item${duplicateCount === 1 ? " is" : "s are"} assigned to multiple stories. Remove each extra assignment before finalizing or adding to a report.`;
    }
    document.querySelectorAll("[data-collab-finalize-action]").forEach((button) => {
      button.disabled = duplicateCount > 0;
      button.title = duplicateCount > 0 ? "Resolve duplicate news items first" : "";
    });
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
    renderChannelInfo();
    renderBriefing();
    renderDecisions();
    renderTasks();
    renderComments();
    renderChat();
    renderActivity();
    renderTimeline();
    renderRoomStory({ forceEditorSync });
    renderDuplicateState();
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
  };

  const applyOptimisticWorkspacePatch = (target, action, data = {}, itemId = null) => {
    const workspaceState = workspace();
    if (target === "channel_info" && action === "set") {
      store.state.channel.workspace = {
        ...workspaceState,
        channel_info: {
          ...(workspaceState.channel_info || {}),
          ...data,
        },
      };
      return;
    }
    const collectionKey = {
      decision: "decisions",
      task: "tasks",
      comment: "comments",
      chat_message: "chat_messages",
      timeline_event: "timeline_events",
    }[target];

    if (!collectionKey) {
      return;
    }

    const items = [...(workspaceState[collectionKey] || [])];
    if (action === "remove") {
      store.state.channel.workspace = {
        ...workspaceState,
        [collectionKey]: items.filter((item) => item.id !== itemId),
      };
      return;
    }

    if (action !== "upsert") {
      return;
    }

    const optimisticId = itemId || data.id || `optimistic-${Date.now()}`;
    const currentUser = data.author || data.owner || currentPresence()?.username || "current user";
    const currentBaseUrl = data.participant_base_url || currentPresence()?.participant_base_url || store.state.channel.active_instance_base_url || "";
    const nextItem = {
      ...data,
      id: optimisticId,
      text: data.text || data.title || "",
      created_at: data.created_at || new Date().toISOString(),
    };
    if (target === "decision") {
      nextItem.owner = nextItem.owner || currentUser;
      nextItem.status = nextItem.status || "open";
    }
    if (target === "task") {
      nextItem.owner = nextItem.owner || currentUser;
      nextItem.status = nextItem.status || "todo";
      nextItem.participant_base_url = nextItem.participant_base_url || currentBaseUrl;
      nextItem.participant_short_name = nextItem.participant_short_name || shortNameFromBaseUrl(currentBaseUrl);
    }
    if (target === "comment" || target === "chat_message") {
      nextItem.author = nextItem.author || currentUser;
      nextItem.participant_base_url = nextItem.participant_base_url || currentBaseUrl;
      nextItem.participant_short_name = nextItem.participant_short_name || shortNameFromBaseUrl(currentBaseUrl);
    }

    const existingIndex = items.findIndex((item) => item.id === optimisticId);
    if (existingIndex >= 0) {
      items[existingIndex] = { ...items[existingIndex], ...nextItem };
    } else {
      items.unshift(nextItem);
    }

    store.state.channel.workspace = {
      ...workspaceState,
      [collectionKey]: items,
    };
  };

  const workspaceActivityText = (target, action) => {
    if (target === "workspace" && action === "set") {
      return "updated workspace view";
    }
    if (target === "briefing" && action === "set") {
      return "updated briefing";
    }
    if (target === "channel_info" && action === "set") {
      return "updated channel info";
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
    syncReportFields(channel);
  };

  const reportControls = (element) => element.matches("input, select, textarea")
    ? [element]
    : Array.from(element.querySelectorAll("input:not([type='hidden']), select, textarea"));

  const reportFieldValue = (element) => {
    if (element.dataset.reportValueType === "list") {
      return reportFieldElements
        .filter((item) => item.dataset.draftId === element.dataset.draftId
          && item.dataset.collabReportField === element.dataset.collabReportField
          && item.checked)
        .map((item) => item.value);
    }
    const controls = reportControls(element);
    const attributeType = element.dataset.reportAttributeType;
    if (attributeType === "STORY") {
      return Array.from(controls[0]?.selectedOptions || []).map((option) => option.value);
    }
    if (attributeType === "RADIO") {
      return controls.find((control) => control.checked)?.value || "";
    }
    if (attributeType === "BOOLEAN") {
      return controls[0]?.checked ? "Yes" : "No";
    }
    if (element.type === "checkbox") {
      return element.checked;
    }
    return controls[0]?.value || "";
  };

  const reportDraft = (channel, draftId) => (channel.report_workspace?.drafts || []).find((draft) => draft.id === draftId);

  const syncReportFields = (channel) => {
    reportFieldElements.forEach((element) => {
      const draft = reportDraft(channel, element.dataset.draftId);
      if (!draft) {
        return;
      }
      let value = draft[element.dataset.collabReportField];
      if (element.dataset.collabReportField.startsWith("attribute:")) {
        const key = element.dataset.collabReportField.slice("attribute:".length);
        value = draft.attributes.find((attribute) => attribute.key === key)?.value ?? "";
      }
      const controls = reportControls(element);
      if (!controls.length) {
        return;
      }
      const attributeType = element.dataset.reportAttributeType;
      if (attributeType === "STORY") {
        const selected = new Set(String(value || "").split(","));
        const available = new Set(draft.selected_story_ids || []);
        Array.from(controls[0]?.options || []).forEach((option) => {
          option.selected = available.has(option.value) && selected.has(option.value);
          option.disabled = !available.has(option.value);
        });
      } else if (attributeType === "RADIO") {
        controls.forEach((control) => {
          control.checked = control.value === value;
        });
      } else if (attributeType === "BOOLEAN") {
        controls[0].checked = value === "Yes";
      } else if (element.dataset.reportValueType === "list") {
        const selected = Array.isArray(value) ? value : String(value || "").split(",");
        element.checked = selected.includes(element.value);
      } else if (element.type === "checkbox") {
        element.checked = Boolean(value);
      } else if (!controls.includes(document.activeElement)) {
        controls[0].value = value ?? "";
      }
      const lock = (channel.report_locks || []).find((item) => item.draft_id === element.dataset.draftId
        && item.field_key === element.dataset.collabReportField);
      const lockedByOther = lock && lock.session_id !== store.state.sessionId;
      controls.forEach((control) => {
        control.disabled = channel.status !== "open" || Boolean(draft.finalized_report_id) || lockedByOther;
      });
      element.title = lockedByOther ? `Locked by ${lock.username || "another user"}` : "";
    });
  };

  const reportLockPayload = (element) => ({
    draft_id: element.dataset.draftId,
    field_key: element.dataset.collabReportField,
  });

  const acquireReportField = (element) => {
    const key = `${element.dataset.draftId}:${element.dataset.collabReportField}`;
    sendMessage("collab.lock.acquire", reportLockPayload(element));
    if (!runtime.reportHeartbeats.has(key)) {
      runtime.reportHeartbeats.set(key, window.setInterval(() => {
        sendMessage("collab.lock.heartbeat", reportLockPayload(element));
      }, 5000));
    }
  };

  const releaseReportField = (element) => {
    const key = `${element.dataset.draftId}:${element.dataset.collabReportField}`;
    window.clearInterval(runtime.reportHeartbeats.get(key));
    runtime.reportHeartbeats.delete(key);
    sendMessage("collab.lock.release", reportLockPayload(element));
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
    if (isReadOnly()) {
      setSaveStatus("Archived channel is read-only.");
      return;
    }
    applyOptimisticWorkspacePatch(target, action, data, itemId);
    appendOptimisticActivity(workspaceActivityText(target, action));
    render();
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
    const mainModeButton = event.target.closest("[data-collab-main-mode]");
    if (mainModeButton) {
      const mode = mainModeButton.dataset.collabMainMode;
      document.querySelectorAll("[data-collab-main-mode]").forEach((button) => {
        button.classList.toggle("tab-active", button.dataset.collabMainMode === mode);
      });
      document.querySelectorAll("[data-collab-main-panel]").forEach((panel) => {
        panel.classList.toggle("hidden", panel.dataset.collabMainPanel !== mode);
      });
      return;
    }

    const reportSelectButton = event.target.closest("[data-collab-report-select]");
    if (reportSelectButton) {
      document.querySelectorAll("[data-collab-report-editor]").forEach((editor) => {
        editor.classList.toggle("hidden", editor.dataset.collabReportEditor !== reportSelectButton.dataset.collabReportSelect);
      });
      return;
    }

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
      if (event.target.closest("[data-collab-remove-story]")) {
        return;
      }
      clearActiveSelection();
      store.switchStory(storyButton.dataset.collabFocusStory);
      sendWorkspacePatch("workspace", "set", { focused_story_id: store.state.selectedStoryId });
      render({ forceEditorSync: true });
      return;
    }

    const removeButton = event.target.closest("[data-collab-item-remove]");
    if (removeButton) {
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
      sendWorkspacePatch(removeButton.dataset.collabItemRemove, "remove", {}, removeButton.dataset.collabItemId);
      return;
    }

    const toggleButton = event.target.closest("[data-collab-item-toggle]");
    if (toggleButton) {
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
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
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
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

    const removeStoryButton = event.target.closest("[data-collab-remove-story]");
    if (removeStoryButton) {
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
      if (!window.confirm("Remove this story from the collaboration channel?")) {
        return;
      }
      setSaveStatus("Removing story...");
      sendMessage("collab.story.remove", {
        snapshot_id: removeStoryButton.dataset.collabRemoveStory,
        selected_story_id: store.state.selectedStoryId,
      });
      return;
    }

    const removeNewsItemButton = event.target.closest("[data-collab-remove-news-item]");
    if (removeNewsItemButton) {
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
      showConfirmDialog({
        title: "Remove channel assignment?",
        text: "This only removes the item from this collaboration story. The persistent news item and its story will not be changed.",
        icon: "warning",
        confirmButtonText: "Remove assignment",
      }).then(({ isConfirmed }) => {
        if (!isConfirmed) {
          return;
        }
        setSaveStatus("Removing news item from collaboration story...");
        sendMessage("collab.news_item.remove", {
          snapshot_id: store.state.selectedStoryId,
          news_item_id: removeNewsItemButton.dataset.collabRemoveNewsItem,
          selected_story_id: store.state.selectedStoryId,
        });
      });
      return;
    }
  });

  document.addEventListener("focusin", (event) => {
    const field = event.target.closest("[data-collab-report-field]");
    if (field && !field.disabled) {
      acquireReportField(field);
    }
  });

  document.addEventListener("focusout", (event) => {
    const field = event.target.closest("[data-collab-report-field]");
    if (field) {
      releaseReportField(field);
    }
  });

  document.addEventListener("change", (event) => {
    const field = event.target.closest("[data-collab-report-field]");
    if (!field || field.disabled) {
      return;
    }
    sendMessage("collab.report.patch", {
      ...reportLockPayload(field),
      value: reportFieldValue(field),
    });
    setSaveStatus("Saving report field...");
  });

  document.addEventListener("submit", (event) => {
    const entryForm = event.target.closest("[data-collab-entry-form]");
    if (entryForm) {
      event.preventDefault();
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
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
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
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
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
      const field = briefingSetForm.dataset.field;
      const value = (new FormData(briefingSetForm).get("value") || "").toString().trim();
      sendWorkspacePatch("briefing", "set", { [field]: value || null });
      briefingSetForm.reset();
      return;
    }

    const channelInfoForm = event.target.closest("[data-collab-channel-info-form]");
    if (channelInfoForm) {
      event.preventDefault();
      if (isReadOnly()) {
        setSaveStatus("Archived channel is read-only.");
        return;
      }
      const formData = new FormData(channelInfoForm);
      sendWorkspacePatch("channel_info", "set", {
        chat_url: (formData.get("chat_url") || "").toString().trim() || null,
        resource_url: (formData.get("resource_url") || "").toString().trim() || null,
        notes: (formData.get("notes") || "").toString().trim() || null,
      });
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
    runtime.reportHeartbeats.forEach((timer) => window.clearInterval(timer));
  }, { once: true });

  mountEditors();
  render({ forceEditorSync: true });
  if (pageData.channel?.status === "open") {
    connect();
  } else {
    setConnectionState("Archived", "rounded-box border border-base-300 bg-base-100 px-4 py-2 text-sm font-medium text-base-content/70");
    setSaveStatus("Archived channel snapshot.");
    syncEditorStory({ force: true });
  }
}());
