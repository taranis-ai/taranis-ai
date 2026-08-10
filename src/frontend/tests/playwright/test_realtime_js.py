from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.sync_api import Page


pytestmark = pytest.mark.e2e_ci

REALTIME_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/realtime.js"


def _load_realtime(
    page: Page,
    *,
    enabled: bool = True,
    page_target: str = "",
    fast_reconnect: bool = False,
    fast_outage: bool = False,
) -> None:
    page.goto(
        "data:text/html,"
        + quote(
            f"""
            <body data-realtime-enabled="{"true" if enabled else "false"}"
                  data-realtime-url="/sse">
              <button type="button" data-realtime-close-on-logout>Logout</button>
              <div id="realtime-status-notification" class="hidden">
                <button type="button" data-realtime-dismiss-status>Dismiss</button>
              </div>
              <div id="realtime-data-notification"
                   class="hidden"
                   data-default-message="New data is available."
                   data-assess-message="New stories are available in Assess."
                   data-default-action="Refresh"
                   data-assess-action="Load new stories">
                <span data-realtime-data-message></span>
                <a data-realtime-refresh href="/current"></a>
                <button type="button" data-realtime-dismiss-data>Dismiss</button>
              </div>
              {f'<div id="{page_target}"></div>' if page_target else ""}
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
    if fast_reconnect or fast_outage:
        page.evaluate(
            """
            ({ fastReconnect, fastOutage }) => {
              const nativeSetTimeout = window.setTimeout.bind(window);
              window.setTimeout = (callback, delay, ...args) => {
                const accelerated =
                  (fastReconnect && delay >= 1000 && delay < 5000) ||
                  (fastOutage && delay === 15000);
                return nativeSetTimeout(callback, accelerated ? 0 : delay, ...args);
              };
              Math.random = () => 0;
            }
            """,
            {"fastReconnect": fast_reconnect, "fastOutage": fast_outage},
        )
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
    _load_realtime(page, page_target="assess", fast_reconnect=True)
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
        }
    """)
    page.wait_for_function("() => EventSource.instances.length === 2")
    page.evaluate("() => EventSource.instances[1].emit('open')")
    page.wait_for_timeout(350)

    assert page.evaluate("() => window.resyncReasons") == ["reconnected"]
    assert "hidden" not in page.locator("#realtime-data-notification").get_attribute("class").split()


def test_protocol_control_and_heartbeat_frames_do_not_resync(page: Page):
    _load_realtime(page, page_target="assess")
    page.evaluate("""
        () => {
          window.resyncReasons = [];
          document.addEventListener(
            "realtime:resync",
            event => window.resyncReasons.push(event.detail.reason),
          );
          const source = EventSource.instances[0];
          source.emit("message", JSON.stringify({ connect: { client: "client-1" } }));
          source.emit("message", JSON.stringify({}));
        }
    """)
    page.wait_for_timeout(350)

    assert page.evaluate("() => window.resyncReasons") == []
    assert "hidden" in page.locator("#realtime-data-notification").get_attribute("class").split()


def test_terminal_disconnect_closes_without_reconnecting(page: Page):
    _load_realtime(page, fast_reconnect=True)
    page.evaluate("""
        () => {
          const source = EventSource.instances[0];
          source.emit("message", JSON.stringify({ disconnect: { code: 4501, reason: "unauthorized" } }));
          source.emit("error");
        }
    """)
    page.wait_for_timeout(50)

    assert page.evaluate("() => EventSource.instances[0].closed") is True
    assert page.evaluate("() => EventSource.instances.length") == 1


def test_assess_event_offers_filtered_htmx_refresh(page: Page):
    _load_realtime(page, page_target="assess")
    page.evaluate("""
        () => {
          window.htmxCalls = [];
          window.htmx = {
            ajax(method, url, options) {
              window.htmxCalls.push({ method, url, options });
              return Promise.resolve();
            },
          };
          EventSource.instances[0].emit("message", JSON.stringify({
            pub: {
              data: {
                v: 1,
                type: "assess.changed",
                change: "invalidated",
                data: {},
              },
            },
          }));
        }
    """)

    notice = page.locator("#realtime-data-notification")
    assert "hidden" not in notice.get_attribute("class").split()
    assert notice.locator("[data-realtime-data-message]").inner_text() == "New stories are available in Assess."
    assert notice.locator("[data-realtime-refresh]").inner_text() == "Load new stories"

    notice.locator("[data-realtime-refresh]").click()
    page.wait_for_function("() => window.htmxCalls.length === 1")

    expected_url = page.evaluate("() => location.pathname + location.search")
    assert page.evaluate("() => window.htmxCalls[0]") == {
        "method": "GET",
        "url": expected_url,
        "options": {"target": "#assess", "select": "#assess", "swap": "outerHTML"},
    }
    assert "hidden" in notice.get_attribute("class").split()


def test_report_event_shows_generic_refresh_notice(page: Page):
    _load_realtime(page, page_target="report")
    page.evaluate("""
        () => EventSource.instances[0].emit("message", JSON.stringify({
          pub: {
            data: {
              v: 1,
              type: "report.item.changed",
              change: "updated",
              data: {},
            },
          },
        }))
    """)

    notice = page.locator("#realtime-data-notification")
    assert "hidden" not in notice.get_attribute("class").split()
    assert notice.locator("[data-realtime-data-message]").inner_text() == "New data is available."
    assert notice.locator("[data-realtime-refresh]").inner_text() == "Refresh"


def test_outage_notice_appears_once_and_clears_on_recovery(page: Page):
    _load_realtime(page, fast_reconnect=True, fast_outage=True)
    page.evaluate("() => EventSource.instances[0].emit('error')")

    notice = page.locator("#realtime-status-notification")
    page.wait_for_function("() => !document.querySelector('#realtime-status-notification').classList.contains('hidden')")
    page.wait_for_function("() => EventSource.instances.length === 2")
    notice.locator("[data-realtime-dismiss-status]").click()
    page.evaluate("() => EventSource.instances[1].emit('error')")
    page.wait_for_function("() => EventSource.instances.length === 3")

    assert "hidden" in notice.get_attribute("class").split()

    page.evaluate("() => EventSource.instances[2].emit('open')")

    assert "hidden" in notice.get_attribute("class").split()


def test_page_restore_reopens_the_connection(page: Page):
    _load_realtime(page)
    page.evaluate("""
        () => {
          EventSource.instances[0].emit("open");
          window.dispatchEvent(new PageTransitionEvent("pagehide"));
          window.dispatchEvent(new PageTransitionEvent("pageshow"));
        }
    """)

    assert page.evaluate("() => EventSource.instances[0].closed") is True
    assert page.evaluate("() => EventSource.instances.length") == 2


def test_logout_closes_event_source(page: Page):
    _load_realtime(page)

    page.locator("[data-realtime-close-on-logout]").click(no_wait_after=True)

    assert page.evaluate("() => EventSource.instances[0].closed") is True
