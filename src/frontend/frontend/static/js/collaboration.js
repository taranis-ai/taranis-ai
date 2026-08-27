const root = document.querySelector("[data-collaboration-document]");
if (root && window.LoroDoc) {
  await window.LoroReady;
  const id = root.dataset.collaborationDocument;
  const input = root.querySelector("textarea");
  const fieldHost = root.querySelector("[data-collaboration-fields]");
  const status = root.querySelector("[data-collaboration-status]");
  const decode = value => Uint8Array.from(atob(value), char => char.charCodeAt(0));
  const encode = value => { let text = ""; for (let index = 0; index < value.length; index += 0x8000) text += String.fromCharCode(...value.subarray(index, index + 0x8000)); return btoa(text); };
  const api = path => `/api${path}`;
  const doc = new window.LoroDoc();
  const session = crypto.randomUUID();
  let version;
  let publishTimer;
  let publishing = false;
  const fieldInputs = new Map();
  const saveLocal = () => localStorage.setItem(`taranis:collab:${id}`, encode(doc.export({ mode: "snapshot" })));
  const render = () => { input.value = doc.getText("title").toString(); for (const [name, field] of fieldInputs) field.value = doc.getText(name).toString(); };
  const bindField = (name, field) => {
    field.value = doc.getText(name).toString();
    fieldInputs.set(name, field);
    field.addEventListener("input", () => { const current = doc.getText(name); current.delete(0, current.length); current.insert(0, field.value); saveLocal(); schedulePublish(); });
  };
  const publish = async () => {
    if (publishing || !version) return;
    const update = doc.export({ mode: "update", from: version });
    if (!update?.length) return;
    publishing = true;
    try {
      const response = await fetch(api(`/documents/${id}/updates`), { method: "POST", headers: { "Content-Type": "application/octet-stream", "X-Update-ID": crypto.randomUUID() }, body: update });
      if (!response.ok) throw new Error("storage");
      version = doc.oplogVersion(); saveLocal(); status.textContent = "Connected and synchronized";
    } catch (_) { saveLocal(); status.textContent = "Working offline — edits preserved locally"; }
    finally { publishing = false; }
  };
  const schedulePublish = () => { clearTimeout(publishTimer); publishTimer = setTimeout(publish, 150); };
  const refreshPresence = () => fetch(api(`/documents/${id}/presence/${session}`), { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ anchor: input.selectionStart, head: input.selectionEnd }) });
  const start = data => {
    doc.import(decode(data.snapshot)); version = doc.oplogVersion(); render();
    for (const name of data.fields ?? []) if (name !== "title") { const label = document.createElement("label"); label.className = "form-control"; const caption = document.createElement("span"); caption.className = "label-text"; caption.textContent = name; const field = document.createElement("textarea"); field.className = "textarea textarea-bordered min-h-32 w-full"; label.append(caption, field); fieldHost.append(label); bindField(name, field); }
    status.textContent = "Connected and synchronized";
    fetch(api(`/documents/${id}/sync`), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ version_vector: encode(version.encode()) }) }).then(response => response.json()).then(sync => { if (sync.update) { doc.import(decode(sync.update)); version = doc.oplogVersion(); render(); } });
    const centrifuge = new window.Centrifuge(`${location.protocol}//${location.host}/collab/connection/websocket`);
    const subscription = centrifuge.newSubscription(`collab:${id}`);
    subscription.on("publication", message => { if (message.data?.update) { doc.import(decode(message.data.update)); version = doc.oplogVersion(); render(); } });
    subscription.on("unsubscribed", () => { status.textContent = "Reconnecting"; }); subscription.subscribe(); centrifuge.connect();
    const onInput = () => { const current = doc.getText("title"); current.delete(0, current.length); current.insert(0, input.value); saveLocal(); schedulePublish(); };
    if (window.TemplateEditor && window.EditorView && window.LoroExtensions) window.TemplateEditor.mount({ textarea: input, options: { lineNumbers: false, extensions: [window.LoroExtensions(doc, undefined, new window.LoroUndoManager(doc, { maxUndoSteps: 100 }), current => current.getText("title")), window.EditorView.updateListener.of(update => { if (update.docChanged) onInput(); })] } });
    else input.addEventListener("input", onInput);
    refreshPresence(); setInterval(refreshPresence, 20000);
    window.addEventListener("pagehide", () => fetch(api(`/documents/${id}/presence/${session}`), { method: "DELETE", keepalive: true }));
  };
  fetch(api(`/documents/${id}`)).then(response => { if (!response.ok) throw new Error("load"); return response.json(); }).then(start).catch(() => {
    const local = localStorage.getItem(`taranis:collab:${id}`);
    if (local) { start({ snapshot: local }); status.textContent = "Working offline — edits preserved locally"; } else status.textContent = "Redis unavailable — read-only";
  });
}
