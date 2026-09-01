import init, { LoroDoc, VersionVector } from "npm:loro-crdt/web";

await init(new URL("../node_modules/.deno/loro-crdt@1.13.2/node_modules/loro-crdt/web/loro_wasm_bg.wasm", import.meta.url));

Deno.test("browser Loro snapshots and updates are idempotent", () => {
  const first = new LoroDoc();
  first.getText("title").insert(0, "alpha");
  first.commit();
  const second = new LoroDoc();
  second.import(first.export({ mode: "snapshot" }));
  const base = second.oplogVersion();
  second.getText("title").insert(5, " bravo");
  second.commit();
  const update = second.export({ mode: "update", from: base });
  const restored = new LoroDoc();
  restored.import(first.export({ mode: "snapshot" }));
  restored.import(update);
  restored.import(update);
  if (restored.getText("title").toString() !== "alpha bravo") throw new Error("Loro update did not converge");
  const missing = restored.export({ mode: "update", from: VersionVector.decode(first.oplogVersion().encode()) });
  if (!missing.length) throw new Error("Loro version vector did not identify missing data");
});
