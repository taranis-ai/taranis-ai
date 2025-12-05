import htmx from "npm:htmx.org";
import Alpine from "npm:alpinejs";

import Sortable from "npm:sortablejs";
import Choices from "npm:choices.js";
import Fuse from "npm:fuse.js";
import Swal from "npm:sweetalert2";
import { highlightSearchTerm } from "npm:highlight-search-term";

import "npm:choices.js/public/assets/styles/choices.min.css";
import "npm:sweetalert2/dist/sweetalert2.min.css";

window.htmx = htmx;
globalThis.htmx = htmx;
window.Alpine = Alpine;
htmx.defineExtension("json-enc", {
  onEvent(name, evt) {
    if (name === "htmx:configRequest") {
      evt.detail.headers["Content-Type"] = "application/json";
    }
  },
  encodeParameters(xhr, parameters) {
    xhr.overrideMimeType("text/json");
    return JSON.stringify(parameters);
  },
});

window.Sortable = Sortable;
window.Choices = Choices;
window.Fuse = Fuse;
window.Swal = Swal;
window.highlightSearchTerm = highlightSearchTerm;

(async () => {
  if (!globalThis.htmx) {
    globalThis.htmx = htmx;
  }
  await Promise.all([
    import("npm:htmx-ext-response-targets"),
  ]);
})();

if (typeof Alpine.start === "function") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      Alpine.start();
    });
  } else {
    Alpine.start();
  }
}
