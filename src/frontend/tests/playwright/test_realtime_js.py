from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.sync_api import Page


pytestmark = pytest.mark.e2e_ci

REALTIME_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/realtime.js"


def _load_realtime(page: Page, *, enabled: bool = True) -> None:
    page.goto(
        "data:text/html,"
        + quote(
            f"""
            <body data-realtime-enabled="{"true" if enabled else "false"}"
                  data-realtime-url="/sse">
              <button type="button" data-realtime-close-on-logout>Logout</button>
            </body>
            """
        )
    )
    page.evaluate("""
        () => {
          window.EventSource = class {
            static instances = [];

            constructor(url) {
              this.url = url;
              this.closed = false;
              this.listeners = new Map();
              EventSource.instances.push(this);
            }

            addEventListener(type, callback) {
              const callbacks = this.listeners.get(type) || [];
              callbacks.push(callback);
              this.listeners.set(type, callbacks);
            }

            emit(type, data = undefined) {
              for (const callback of this.listeners.get(type) || []) {
                callback(data === undefined ? {} : { data });
              }
            }

            close() {
              this.closed = true;
            }
          };
        }
    """)
    page.add_script_tag(path=str(REALTIME_JS_PATH))


def test_realtime_disabled_creates_no_event_source(page: Page):
    _load_realtime(page, enabled=False)

    assert page.evaluate("() => EventSource.instances.length") == 0


def test_realtime_owns_one_event_source_and_dispatches_valid_domain_event(page: Page):
    _load_realtime(page)
    page.evaluate("""
        () => {
          window.receivedRealtimeEvents = [];
          document.addEventListener(
            "realtime:report.item.changed",
            event => window.receivedRealtimeEvents.push(event.detail),
          );
          EventSource.instances[0].emit("message", JSON.stringify({
            pub: {
              data: {
                v: 1,
                id: "019f8fb3-7ca2-74cb-83c5-a72ef719c93e",
                type: "report.item.changed",
                occurred_at: "2026-07-23T18:00:00.000Z",
                change: "updated",
                resource: {
                  kind: "report_item",
                  id: "019f8fb3-7ca2-74cb-83c5-a72ef719c93f",
                },
                data: {},
              },
            },
          }));
        }
    """)

    assert page.evaluate("() => EventSource.instances.length") == 1
    assert page.evaluate("() => window.receivedRealtimeEvents.length") == 1


def test_reconnect_emits_one_debounced_resynchronization(page: Page):
    _load_realtime(page)
    page.evaluate("""
        () => {
          window.resyncReasons = [];
          document.addEventListener(
            "realtime:resync",
            event => window.resyncReasons.push(event.detail.reason),
          );
          const source = EventSource.instances[0];
          source.emit("open");
          source.emit("error");
          source.emit("open");
          source.emit("error");
          source.emit("open");
        }
    """)
    page.wait_for_timeout(350)

    assert page.evaluate("() => window.resyncReasons") == ["reconnected"]


def test_logout_closes_event_source(page: Page):
    _load_realtime(page)

    page.locator("[data-realtime-close-on-logout]").click(no_wait_after=True)

    assert page.evaluate("() => EventSource.instances[0].closed") is True
