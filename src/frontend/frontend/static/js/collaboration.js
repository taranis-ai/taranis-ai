const root = document.querySelector("[data-collaboration-document]");
if (root) {
  if (!window.LoroDoc) await new Promise(resolve => window.addEventListener("loro-ready", resolve, { once: true }));
  await window.LoroReady;
  const id = root.dataset.collaborationDocument;
  const input = root.querySelector("textarea");
  const fieldHost = root.querySelector("[data-collaboration-fields]");
  const status = root.querySelector("[data-collaboration-status]");
  const presenceList = root.querySelector("[data-collaboration-presence-list]");
  const presenceCount = root.querySelector("[data-collaboration-presence-count]");
  const decode = value => Uint8Array.from(atob(value), char => char.charCodeAt(0));
  const encode = value => { let text = ""; for (let index = 0; index < value.length; index += 0x8000) text += String.fromCharCode(...value.subarray(index, index + 0x8000)); return btoa(text); };
  const uuid = () => { if (typeof crypto.randomUUID === "function") return crypto.randomUUID(); const bytes = new Uint8Array(16); crypto.getRandomValues(bytes); bytes[6] = bytes[6] & 15 | 64; bytes[8] = bytes[8] & 63 | 128; return [...bytes].map((value, index) => (index === 4 || index === 6 || index === 8 || index === 10 ? "-" : "") + value.toString(16).padStart(2, "0")).join(""); };
  const api = path => `/api${path}`;
  const csrfHeaders = () => ({ "X-CSRF-TOKEN": typeof getCSRFToken === "function" ? getCSRFToken() || "" : "" });
  const doc = new window.LoroDoc();
  const session = uuid();
  let version;
  let publishTimer;
  let publishing = false;
  const fieldInputs = new Map();
  const richViews = new Map();
  let documentData;
  const activePresence = new Map();
  const escapeHtml = value => String(value ?? "").replace(/[&<>\"']/g, character => ({"&":"&amp;", "<":"&lt;", ">":"&gt;", "\"":"&quot;", "'":"&#39;"}[character]));
  const saveLocal = () => localStorage.setItem(`taranis:collab:${id}`, encode(doc.export({ mode: "snapshot" })));
  const renderPresence = values => {
    activePresence.clear();
    for (const value of values ?? []) if (value?.session_id) activePresence.set(value.session_id, value);
    const users = [...activePresence.values()];
    presenceCount.textContent = `${users.length} active`;
    presenceList.innerHTML = users.length ? users.map(value => `<span class="badge badge-outline gap-2"><span class="h-2 w-2 rounded-full bg-success"></span>${escapeHtml(value.name || value.user_id || "User")}</span>`).join("") : '<span class="text-sm opacity-60">No other users are editing this document.</span>';
  };
  const controlValue = (field, type) => type === "BOOLEAN" ? (field.checked ? "Yes" : "No") : type === "STORY" ? [...field.selectedOptions].map(option => option.value).join(",") : field.value;
  const setControlValue = (field, type, value) => {
    if (type === "BOOLEAN") field.checked = value.toLowerCase() === "yes" || value.toLowerCase() === "true";
    else if (type === "STORY") { const selected = new Set(value.split(",").filter(Boolean)); [...field.options].forEach(option => { option.selected = selected.has(option.value); }); }
    else field.value = value;
  };
  const render = () => { input.value = doc.getText("title").toString(); for (const [name, field] of fieldInputs) if (!richViews.has(name)) setControlValue(field, documentData.field_metadata?.[name]?.type ?? "TEXT", doc.getText(name).toString()); };
  const renderNews = () => {
    const list = root.querySelector("[data-collaboration-news-list]");
    if (!list) return;
    const items = documentData?.story?.story?.news_items ?? [];
    const targets = (documentData?.channel_stories ?? []).filter(story => story.id !== documentData.resource_id);
    list.innerHTML = items.length ? items.map(item => `<details class="rounded border border-base-300 p-3"><summary class="cursor-pointer font-medium">${escapeHtml(item.title || item.id)}</summary><p class="mt-2 whitespace-pre-line text-sm opacity-70">${escapeHtml(item.description || item.content || "")}</p><div class="mt-3 flex flex-wrap items-center gap-2"><button class="btn btn-ghost btn-xs text-error" type="button" data-remove-news="${escapeHtml(item.id)}">Remove</button>${targets.length ? `<label class="text-xs opacity-70" for="move-${escapeHtml(item.id)}">Move to</label><select class="select select-bordered select-xs" id="move-${escapeHtml(item.id)}" data-move-target="${escapeHtml(item.id)}"><option value="">Choose story</option>${targets.map(story => `<option value="${escapeHtml(story.id)}">${escapeHtml(story.title || story.id)}</option>`).join("")}</select><button class="btn btn-outline btn-xs" type="button" data-move-news="${escapeHtml(item.id)}">Move</button>` : ""}</div></details>`).join("") : '<p class="text-sm opacity-60">No news items.</p>';
    list.querySelectorAll("[data-remove-news]").forEach(button => button.addEventListener("click", async () => {
      const response = await fetch(api(`/collaboration/channels/${documentData.channel_id}/remove-news-item`), { method: "POST", headers: { ...csrfHeaders(), "Content-Type": "application/json" }, body: JSON.stringify({ source_snapshot_id: documentData.resource_id, news_item_id: button.dataset.removeNews }) });
      if (response.status === 202) { status.textContent = "Removal pending owner approval"; return; }
      if (!response.ok) { status.textContent = "Unable to remove news item"; return; }
      const result = await response.json(); documentData.channel_stories = result.stories ?? documentData.channel_stories; documentData.story = documentData.channel_stories.find(story => story.id === documentData.resource_id) ?? documentData.story; renderNews();
    }));
    list.querySelectorAll("[data-move-news]").forEach(button => button.addEventListener("click", async () => {
      const newsItemId = button.dataset.moveNews;
      const target = list.querySelector(`[data-move-target="${CSS.escape(newsItemId)}"]`);
      if (!target?.value) return;
      button.disabled = true;
      const response = await fetch(api(`/collaboration/channels/${documentData.channel_id}/move-news-item`), { method: "POST", headers: { ...csrfHeaders(), "Content-Type": "application/json" }, body: JSON.stringify({ source_snapshot_id: documentData.resource_id, target_snapshot_id: target.value, news_item_id: newsItemId }) });
      if (response.status === 202) {
        status.textContent = "Move pending owner approval";
        button.disabled = false;
      } else if (response.ok) {
        const result = await response.json();
        documentData.channel_stories = result.stories ?? documentData.channel_stories;
        documentData.story = documentData.channel_stories.find(story => story.id === documentData.resource_id) ?? documentData.story;
        renderNews();
      } else { status.textContent = response.status === 503 ? "Owner unavailable — move queued" : "Unable to move news item"; button.disabled = false; }
    }));
  };
  const bindField = (name, field, type = "TEXT") => {
    setControlValue(field, type, doc.getText(name).toString());
    fieldInputs.set(name, field);
    field.addEventListener(type === "BOOLEAN" || type === "STORY" || ["ENUM", "CPE", "RADIO"].includes(type) ? "change" : "input", () => { const current = doc.getText(name); current.delete(0, current.length); current.insert(0, controlValue(field, type)); doc.commit(); saveLocal(); schedulePublish(); });
  };
  const publish = async () => {
    if (publishing || !version) return;
    const update = doc.export({ mode: "update", from: version });
    if (!update?.length) return;
    publishing = true;
    try {
      const response = await fetch(api(`/documents/${id}/updates`), { method: "POST", headers: { ...csrfHeaders(), "Content-Type": "application/octet-stream", "X-Update-ID": uuid() }, body: update });
      if (!response.ok) throw new Error("storage");
      version = doc.oplogVersion(); saveLocal(); status.textContent = "Connected and synchronized";
    } catch (_) { saveLocal(); status.textContent = "Working offline — edits preserved locally"; }
    finally { publishing = false; }
  };
  const schedulePublish = () => { clearTimeout(publishTimer); publishTimer = setTimeout(publish, 150); };
  const refreshPresence = () => fetch(api(`/documents/${id}/presence/${session}`), { method: "PUT", headers: { ...csrfHeaders(), "Content-Type": "application/json" }, body: JSON.stringify({ anchor: input.selectionStart, head: input.selectionEnd }) });
  const loadPresence = () => fetch(api(`/documents/${id}/presence/${session}`)).then(response => response.ok ? response.json() : null).then(value => { if (value) renderPresence(value.presence); }).catch(() => {});
  const start = data => {
    documentData = data;
    renderPresence(data.presence);
    doc.import(decode(data.snapshot)); version = doc.oplogVersion(); render();
    for (const name of data.fields ?? []) if (name !== "title") {
      const metadata = data.field_metadata?.[name] ?? {};
      const type = metadata.type ?? data.field_types?.[name] ?? "TEXT";
      const rich = data.rich_fields?.includes(name);
      if (!rich && !doc.getText(name).toString() && data.initial_fields?.[name]) {
        doc.getText(name).insert(0, data.initial_fields[name]);
        doc.commit();
      }
      const label = document.createElement("label"); label.className = "form-control";
      const caption = document.createElement("span"); caption.className = "label-text"; caption.textContent = metadata.title || name;
      if (metadata.required) caption.textContent += " *";
      let field;
      if (type === "BOOLEAN") { field = document.createElement("input"); field.type = "checkbox"; field.className = "toggle toggle-primary"; }
      else if (["ENUM", "CPE", "RADIO", "STORY"].includes(type)) { field = document.createElement("select"); field.className = "select select-bordered w-full"; if (type === "STORY") field.multiple = true; for (const option of metadata.options ?? []) { const element = document.createElement("option"); element.value = option.value; element.textContent = option.label; field.append(element); } }
      else { field = document.createElement(type === "NUMBER" ? "input" : "textarea"); if (type === "NUMBER") field.type = "number"; else if (["DATE", "TIME", "DATE_TIME"].includes(type)) field.type = ({ DATE: "date", TIME: "time", DATE_TIME: "datetime-local" })[type]; field.className = rich ? "sr-only" : type === "TEXT" ? "textarea textarea-bordered min-h-32 w-full" : "input input-bordered w-full"; }
      field.dataset.richText = rich ? "true" : "false";
      if (metadata.description) field.title = metadata.description, field.placeholder = metadata.description;
      label.append(caption, field);
      if (rich && window.ProseMirrorSchema && window.ProseMirrorState && window.ProseMirrorView && window.LoroSyncPlugin) {
        const host = document.createElement("div"); host.className = "min-h-32 rounded border border-base-300 p-3";
        label.append(host); fieldHost.append(label); fieldInputs.set(name, field);
        const initial = data.initial_fields?.[name] ?? "";
        const paragraph = window.ProseMirrorSchema.nodes.paragraph.create();
        const state = window.ProseMirrorState.create({ schema: window.ProseMirrorSchema, doc: window.ProseMirrorSchema.nodes.doc.create(null, paragraph), plugins: [window.LoroSyncPlugin({ doc, containerId: doc.getMap(name).id }), window.LoroUndoPlugin({ doc, undoManager: new window.LoroUndoManager(doc, { maxUndoSteps: 100 }) })] });
        const view = new window.ProseMirrorView(host, { state, dispatchTransaction(transaction) { const next = view.state.apply(transaction); view.updateState(next); field.value = host.textContent || ""; saveLocal(); schedulePublish(); } });
        if (initial && doc.getMap(name).size === 0) view.dispatch(view.state.tr.insert(1, window.ProseMirrorSchema.text(initial)));
        richViews.set(name, view);
      } else { fieldHost.append(label); bindField(name, field, type); }
    }
    renderNews();
    status.textContent = "Connected and synchronized";
    fetch(api(`/documents/${id}/sync`), { method: "POST", headers: { ...csrfHeaders(), "Content-Type": "application/json" }, body: JSON.stringify({ version_vector: encode(version.encode()) }) }).then(response => response.json()).then(sync => { if (sync.update) { doc.import(decode(sync.update)); version = doc.oplogVersion(); render(); } });
    const onInput = () => { const current = doc.getText("title"); current.delete(0, current.length); current.insert(0, input.value); doc.commit(); saveLocal(); schedulePublish(); };
    refreshPresence(); loadPresence(); setInterval(() => { refreshPresence(); loadPresence(); }, 20000);
    try {
      const websocketProtocol = location.protocol === "https:" ? "wss:" : "ws:";
      const centrifuge = new window.Centrifuge(`${websocketProtocol}//${location.host}/collab/connection/websocket`);
      const subscription = centrifuge.newSubscription(`collab:${id}`);
      subscription.on("publication", message => {
        const data = message.data?.data ?? {};
        if (data.update) { doc.import(decode(data.update)); version = doc.oplogVersion(); render(); }
        if (data.session_id && data.name) renderPresence([...activePresence.values(), data]);
        if (data.session_id && !data.name) renderPresence([...activePresence.values()].filter(value => value.session_id !== data.session_id));
      });
      subscription.on("unsubscribed", () => { status.textContent = "Reconnecting"; }); subscription.subscribe(); centrifuge.connect();
    } catch (_) { status.textContent = "Reconnecting"; }
    try {
      if (!window.TemplateEditor || !window.EditorView || !window.LoroExtensions) throw new Error("editor unavailable");
      window.TemplateEditor.mount({ textarea: input, options: { lineNumbers: false, extensions: [window.LoroExtensions(doc, undefined, new window.LoroUndoManager(doc, { maxUndoSteps: 100 }), current => current.getText("title")), window.EditorView.updateListener.of(update => { if (update.docChanged) onInput(); })] } });
    } catch (_) { input.classList.remove("hidden"); input.addEventListener("input", onInput); }
    window.addEventListener("pagehide", () => fetch(api(`/documents/${id}/presence/${session}`), { method: "DELETE", headers: csrfHeaders(), keepalive: true }));
  };
  fetch(api(`/documents/${id}`)).then(response => { if (!response.ok) throw new Error("load"); return response.json(); }).then(data => {
    try { start(data); }
    catch (error) { console.error("Collaboration editor initialization failed", error); status.textContent = "Unable to initialize editor"; }
  }, () => {
    const local = localStorage.getItem(`taranis:collab:${id}`);
    if (local) { start({ snapshot: local }); status.textContent = "Working offline — edits preserved locally"; } else status.textContent = "Redis unavailable — read-only";
  });
}
