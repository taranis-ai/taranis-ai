import { EditorState } from "npm:@codemirror/state";
import {
  EditorView,
  highlightActiveLine,
  keymap,
  lineNumbers,
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
import { basicSetup } from "codemirror";
import { unifiedMergeView } from "@codemirror/merge";

window.EditorView = EditorView;
window.EditorState = EditorState;
window.basicSetup = basicSetup;


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

  const editorExtensionsList = [window.basicSetup];

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

window.TemplateEditor = { mount, mountUnifiedMerge };
