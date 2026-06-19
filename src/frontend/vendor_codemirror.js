import { Compartment, EditorSelection, EditorState, RangeSetBuilder, StateEffect, StateField } from "npm:@codemirror/state";
import {
  Decoration,
  EditorView,
  highlightActiveLine,
  keymap,
  lineNumbers,
  WidgetType,
} from "npm:@codemirror/view";
import {
  defaultKeymap,
  history,
  historyKeymap,
  indentWithTab,
} from "npm:@codemirror/commands";
import {
  StreamLanguage,
  bracketMatching,
  defaultHighlightStyle,
  indentUnit,
  syntaxHighlighting,
} from "npm:@codemirror/language";
import { jinja2 } from "npm:@codemirror/legacy-modes/mode/jinja2";
import { unifiedMergeView } from "@codemirror/merge";

window.EditorView = EditorView;
window.EditorState = EditorState;

const setRemoteSelectionsEffect = StateEffect.define();
const remoteSelectionsField = StateField.define({
  create() {
    return Decoration.none;
  },
  update(decorations, transaction) {
    for (const effect of transaction.effects) {
      if (effect.is(setRemoteSelectionsEffect)) {
        return effect.value;
      }
    }
    if (transaction.docChanged) {
      return decorations.map(transaction.changes);
    }
    return decorations;
  },
  provide(field) {
    return EditorView.decorations.from(field);
  },
});

class RemoteCaretWidget extends WidgetType {
  constructor(color, username) {
    super();
    this.color = color;
    this.username = username;
  }

  toDOM() {
    const wrapper = document.createElement("span");
    wrapper.className = "cm-remote-caret";
    wrapper.style.borderLeft = `2px solid ${this.color}`;
    wrapper.style.marginLeft = "-1px";
    wrapper.style.height = "1.2em";
    wrapper.style.display = "inline-block";
    wrapper.style.verticalAlign = "text-top";
    wrapper.title = this.username;
    return wrapper;
  }
}


const DEFAULT_OPTIONS = {
  language: StreamLanguage.define(jinja2),
  lineNumbers: true,
  lineWrapping: true,
  indentUnit: 2,
  tabSize: 2,
  styleActiveLine: true,
  matchBrackets: true,
  extensions: [],
};

function ensureHost(textarea, parent) {
  if (parent) {
    parent.innerHTML = "";
    parent.classList.remove("hidden");
    parent.style.position = parent.style.position || "relative";
    return parent;
  }

  const wrapper = document.createElement("div");
  wrapper.className = "codemirror-wrapper";
  wrapper.style.width = "100%";
  wrapper.style.height = "100%";
  textarea.insertAdjacentElement("afterend", wrapper);
  return wrapper;
}

function buildExtensions(options) {
  const extensions = [
    history(),
    keymap.of([
      ...defaultKeymap,
      ...historyKeymap,
      indentWithTab,
    ]),
    syntaxHighlighting(defaultHighlightStyle, { fallback: true }),
  ];

  if (options.language) {
    extensions.push(options.language);
  }

  if (options.lineNumbers) {
    extensions.push(lineNumbers());
  }

  if (options.styleActiveLine) {
    extensions.push(highlightActiveLine());
  }

  if (options.lineWrapping) {
    extensions.push(EditorView.lineWrapping);
  }

  if (options.matchBrackets) {
    extensions.push(bracketMatching());
  }

  if (options.indentUnit) {
    extensions.push(indentUnit.of(" ".repeat(options.indentUnit)));
  }

  if (options.tabSize) {
    extensions.push(EditorState.tabSize.of(options.tabSize));
  }

  if (Array.isArray(options.extensions) && options.extensions.length) {
    extensions.push(...options.extensions);
  }

  return extensions;
}

function mount({ textarea, parent, options = {} }) {
  if (!textarea) {
    console.warn("TemplateEditor: textarea element is required.");
    return null;
  }

  const host = ensureHost(textarea, parent ?? textarea.parentElement);
  textarea.classList.add("hidden");

  const resolvedOptions = {
    ...DEFAULT_OPTIONS,
    ...options,
  };

  const syncValue = (state) => {
    const value = state.doc.toString();
    textarea.value = value;
    return value;
  };

  const extensions = [
    ...buildExtensions(resolvedOptions),
    EditorView.updateListener.of((update) => {
      if (update.docChanged) {
        syncValue(update.state);
      }
    }),
  ];

  const state = EditorState.create({
    doc: textarea.value ?? "",
    extensions,
  });

  const view = new EditorView({
    state,
    parent: host,
  });

  view.dom.style.height = "100%";
  view.dom.style.width = "100%";

  const sync = () => syncValue(view.state);

  return {
    editor: view,
    sync,
    destroy() {
      sync();
      view.destroy();
      textarea.classList.remove("hidden");
    },
  };
}

function mountUnifiedMerge({ parent, originalDoc, newDoc, options = {} }) {
  if (!parent) return null;

  parent.innerHTML = "";
  parent.classList.remove("hidden");

  const {
    lineWrapping = true,
    editorExtensions = [],
    ...mergeOptions
  } = options;

  const editorExtensionsList = buildExtensions({
    ...DEFAULT_OPTIONS,
    ...options,
    extensions: options.editorExtensions ?? [],
  });
  if (lineWrapping) {
    editorExtensionsList.push(EditorView.lineWrapping);
  }

  if (Array.isArray(editorExtensions) && editorExtensions.length) {
    editorExtensionsList.push(...editorExtensions);
  }

  editorExtensionsList.push(
    unifiedMergeView({
      original: originalDoc,
      highlightChanges: true,
      gutter: true,
      allowInlineDiffs: true,
      mergeControls: true,
      collapseUnchanged: { margin: 3, minSize: 4 },
      ...mergeOptions,
    }),
  );

  return new window.EditorView({
      doc: newDoc,
      extensions: editorExtensionsList,
      parent: parent,
    });
}

function selectionColor(seed) {
  let hash = 0;
  for (const char of String(seed || "")) {
    hash = ((hash << 5) - hash) + char.charCodeAt(0);
    hash |= 0;
  }
  return Math.abs(hash) % 360;
}

function buildRemoteSelectionDecorations(selections) {
  const builder = new RangeSetBuilder();
  for (const selection of selections || []) {
    const hue = selectionColor(selection.session_id || selection.username);
    const color = `hsl(${hue} 70% 45%)`;
    const selectionColorValue = `hsl(${hue} 80% 75% / 0.35)`;
    const start = Math.max(0, Math.min(selection.anchor, selection.head));
    const end = Math.max(0, Math.max(selection.anchor, selection.head));
    if (start !== end) {
      builder.add(start, end, Decoration.mark({
        attributes: {
          style: `background-color:${selectionColorValue}`,
          title: selection.username || "Collaborator",
        },
      }));
    }
    builder.add(end, end, Decoration.widget({
      widget: new RemoteCaretWidget(color, selection.username || "Collaborator"),
      side: 1,
    }));
  }
  return builder.finish();
}

function mountShared({ textarea, parent, options = {}, onChange, onFocus, onBlur, onSelectionChange }) {
  if (!textarea) {
    console.warn("CollabEditor: textarea element is required.");
    return null;
  }

  const host = ensureHost(textarea, parent ?? textarea.parentElement);
  textarea.classList.add("hidden");

  const editableCompartment = new Compartment();
  let suppressChange = false;
  let blurTimer = null;

  const syncValue = (state) => {
    textarea.value = state.doc.toString();
    return textarea.value;
  };

  const extensions = [
    ...buildExtensions({
      ...DEFAULT_OPTIONS,
      lineNumbers: false,
      styleActiveLine: false,
      matchBrackets: false,
      ...options,
    }),
    editableCompartment.of(EditorView.editable.of(true)),
    remoteSelectionsField,
    EditorView.theme({
      "&": { minHeight: options.minHeight || "7rem", fontSize: "0.95rem" },
      ".cm-scroller": { fontFamily: "inherit", lineHeight: "1.5" },
      ".cm-content": { padding: "0.9rem 1rem" },
      ".cm-focused": { outline: "none" },
    }),
    EditorView.domEventHandlers({
      focus() {
        if (blurTimer) {
          window.clearTimeout(blurTimer);
          blurTimer = null;
        }
        onFocus?.();
      },
      blur() {
        blurTimer = window.setTimeout(() => onBlur?.(), 0);
      },
    }),
    EditorView.updateListener.of((update) => {
      syncValue(update.state);
      if (update.docChanged && !suppressChange) {
        const changes = [];
        update.changes.iterChanges((fromA, toA, _fromB, _toB, inserted) => {
          changes.push({ from: fromA, to: toA, insert: inserted.toString() });
        });
        onChange?.({ changes, doc: update.state.doc.toString() });
      }
      if ((update.selectionSet || update.focusChanged) && update.view.hasFocus) {
        const selection = update.state.selection.main;
        onSelectionChange?.({ anchor: selection.anchor, head: selection.head });
      }
    }),
  ];

  const state = EditorState.create({
    doc: textarea.value ?? "",
    extensions,
  });
  const view = new EditorView({ state, parent: host });
  view.dom.style.width = "100%";

  return {
    editor: view,
    sync() {
      return syncValue(view.state);
    },
    focus() {
      view.focus();
    },
    setEditable(editable) {
      view.dispatch({ effects: editableCompartment.reconfigure(EditorView.editable.of(Boolean(editable))) });
    },
    setText(text) {
      suppressChange = true;
      view.dispatch({
        changes: { from: 0, to: view.state.doc.length, insert: text ?? "" },
        selection: EditorSelection.cursor(Math.min(view.state.selection.main.head, (text ?? "").length)),
      });
      suppressChange = false;
      syncValue(view.state);
    },
    applyRemoteChanges(changes) {
      if (!changes?.length) return;
      suppressChange = true;
      view.dispatch({ changes });
      suppressChange = false;
      syncValue(view.state);
    },
    getSelection() {
      return view.state.selection.main;
    },
    hasFocus() {
      return view.hasFocus;
    },
    setRemoteSelections(selections) {
      view.dispatch({ effects: setRemoteSelectionsEffect.of(buildRemoteSelectionDecorations(selections)) });
    },
    destroy() {
      syncValue(view.state);
      view.destroy();
      textarea.classList.remove("hidden");
      host.innerHTML = "";
    },
  };
}

window.TemplateEditor = { mount, mountUnifiedMerge };
window.CollabEditor = { mountShared, selectionColor };
