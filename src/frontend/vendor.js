import htmx from "npm:htmx.org";
import htmxResponseTargets from "npm:htmx-ext-response-targets";
import Alpine from "npm:alpinejs";

import Sortable from "npm:sortablejs";
import Choices from "npm:choices.js";
import Fuse from "npm:fuse.js";
import Swal from "npm:sweetalert2";
import { highlightSearchTerm } from "npm:highlight-search-term";

import "npm:choices.js/public/assets/styles/choices.min.css";
import "npm:sweetalert2/dist/sweetalert2.min.css";

window.htmx = htmx;
window.Alpine = Alpine;

window.Sortable = Sortable;
window.Choices = Choices;
window.Fuse = Fuse;
window.Swal = Swal;
window.highlightSearchTerm = highlightSearchTerm;

if (typeof Alpine.start === "function") {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => {
      Alpine.start();
    });
  } else {
    Alpine.start();
  }
}
