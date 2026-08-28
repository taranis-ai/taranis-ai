import init, { LoroDoc } from "npm:loro-crdt/web";
import { Centrifuge } from "npm:centrifuge";
import { LoroExtensions } from "npm:loro-codemirror";
import { LoroSyncPlugin, LoroUndoPlugin } from "npm:loro-prosemirror";
import { UndoManager } from "npm:loro-crdt";
import { Schema, DOMSerializer } from "npm:prosemirror-model";
import { EditorState } from "npm:prosemirror-state";
import { EditorView } from "npm:prosemirror-view";
import { schema as basicSchema } from "npm:prosemirror-schema-basic";
import { addListNodes } from "npm:prosemirror-schema-list";

const prosemirrorSchema = new Schema({
  nodes: addListNodes(basicSchema.spec.nodes, "paragraph block*", "block"),
  marks: basicSchema.spec.marks,
});

window.LoroDoc = LoroDoc;
window.Centrifuge = Centrifuge;
window.LoroExtensions = LoroExtensions;
window.LoroSyncPlugin = LoroSyncPlugin;
window.LoroUndoPlugin = LoroUndoPlugin;
window.LoroUndoManager = UndoManager;
window.ProseMirrorSchema = prosemirrorSchema;
window.ProseMirrorState = EditorState;
window.ProseMirrorView = EditorView;
window.ProseMirrorSerializer = DOMSerializer;
window.LoroReady = init("/static/vendor/loro_wasm_bg.wasm");
