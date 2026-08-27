import init, { LoroDoc } from "npm:loro-crdt/web";
import { Centrifuge } from "npm:centrifuge";
import { LoroExtensions } from "npm:loro-codemirror";
import { LoroSyncPlugin, LoroUndoPlugin } from "npm:loro-prosemirror";
import { UndoManager } from "npm:loro-crdt";

window.LoroDoc = LoroDoc;
window.Centrifuge = Centrifuge;
window.LoroExtensions = LoroExtensions;
window.LoroSyncPlugin = LoroSyncPlugin;
window.LoroUndoPlugin = LoroUndoPlugin;
window.LoroUndoManager = UndoManager;
window.LoroReady = init("/static/vendor/loro_wasm_bg.wasm");
