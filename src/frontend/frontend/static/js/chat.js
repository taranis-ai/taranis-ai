(function () {
  function scrollToLatest(workspace) {
    const messages = workspace.querySelector("#chat-messages");
    if (messages) {
      messages.scrollTop = messages.scrollHeight;
    }
  }

  function stageLabel(workspace, stage) {
    const labels = {
      planning: workspace.dataset.chatStagePlanning,
      searching: workspace.dataset.chatStageSearching,
      answering: workspace.dataset.chatStageAnswering,
    };
    return labels[stage] || labels.planning;
  }

  function begin(form) {
    const workspace = form.closest("#chat-workspace");
    const input = form.querySelector("#chat-message-input");
    const pending = workspace?.querySelector("[data-chat-pending-user]");
    const pendingContent = workspace?.querySelector(
      "[data-chat-pending-user-content]",
    );
    if (!workspace || !input || !pending || !pendingContent) {
      return;
    }

    workspace.dataset.chatSequence = "0";
    pendingContent.textContent = input.value;
    pending.classList.remove("hidden");
    workspace.querySelector("[data-chat-empty]")?.classList.add("hidden");
    const streamContent = workspace.querySelector("[data-chat-stream-content]");
    const streamStatus = workspace.querySelector("[data-chat-stream-status]");
    const streamStage = workspace.querySelector("[data-chat-stream-stage]");
    if (streamContent && streamStatus && streamStage) {
      streamContent.textContent = "";
      streamContent.classList.add("hidden");
      streamStatus.classList.remove("hidden");
      streamStage.textContent = stageLabel(workspace, "planning");
    }
    input.value = "";
    scrollToLatest(workspace);
  }

  function update(event) {
    const data = event?.data;
    const workspace = document.getElementById("chat-workspace");
    if (
      !workspace ||
      data?.turn_id !== workspace.dataset.chatTurnId ||
      !Number.isInteger(data.sequence) ||
      data.sequence <= Number(workspace.dataset.chatSequence || 0) ||
      typeof data.content !== "string"
    ) {
      return;
    }

    workspace.dataset.chatSequence = String(data.sequence);
    const streamContent = workspace.querySelector("[data-chat-stream-content]");
    const streamStatus = workspace.querySelector("[data-chat-stream-status]");
    const streamStage = workspace.querySelector("[data-chat-stream-stage]");
    if (!streamContent || !streamStatus || !streamStage) {
      return;
    }
    streamStage.textContent = stageLabel(workspace, data.stage);
    streamContent.textContent = data.content;
    streamContent.classList.toggle("hidden", !data.content);
    streamStatus.classList.toggle("hidden", Boolean(data.content));
    scrollToLatest(workspace);
  }

  self.taranisChat = { begin, update };
})();
