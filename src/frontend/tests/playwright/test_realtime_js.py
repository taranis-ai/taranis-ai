from pathlib import Path
from urllib.parse import quote

import pytest
from playwright.sync_api import Page


pytestmark = pytest.mark.e2e_ci

REALTIME_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/realtime.js"
CHAT_JS_PATH = Path(__file__).parents[2] / "frontend/static/js/chat.js"
VENDOR_JS_PATH = Path(__file__).parents[2] / "frontend/static/vendor/vendor.bundle.js"


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
              <div id="realtime-broadcast-notifications"></div>
              <template id="realtime-broadcast-notification-template">
                <div data-realtime-broadcast-notification>
                  <span data-realtime-broadcast-message></span>
                  <button type="button" data-realtime-dismiss-broadcast>Dismiss</button>
                </div>
              </template>
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
              window.reconnectDelays = [];
              window.setTimeout = (callback, delay, ...args) => {
                const reconnect = fastReconnect && delay >= 1000 && delay <= 61000 && delay !== 15000;
                if (reconnect) window.reconnectDelays.push(delay);
                const accelerated =
                  reconnect ||
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


def test_chat_stream_shows_optimistic_message_and_applies_newest_matching_snapshot(page: Page):
    page.set_content(
        """
        <div id="chat-workspace" data-chat-turn-id="turn-1" data-chat-sequence="0"
             data-chat-stage-planning="Planning" data-chat-stage-answering="Writing">
          <div id="chat-messages"><div data-chat-empty></div>
            <div class="hidden" data-chat-pending-user><span data-chat-pending-user-content></span></div>
            <div data-chat-stream-status><span data-chat-stream-stage></span></div><span data-chat-stream-content></span></div>
          <form><textarea id="chat-message-input">Question</textarea></form>
        </div>
        """
    )
    page.add_script_tag(path=str(CHAT_JS_PATH))
    page.evaluate(
        """
        () => {
          taranisChat.begin(document.querySelector("#chat-workspace form"));
          for (const [turn_id, sequence, content] of [
            ["other-turn", 1, "Wrong"],
            ["turn-1", 2, '<img src=x onerror="alert(1)">Safe'],
            ["turn-1", 1, "Stale"],
          ]) taranisChat.update({data: {turn_id, sequence, stage: "answering", content}});
        }
        """
    )

    assert page.locator("[data-chat-pending-user-content]").text_content() == "Question"
    assert page.locator("#chat-message-input").input_value() == ""
    assert page.locator("[data-chat-stream-content]").text_content() == '<img src=x onerror="alert(1)">Safe'
    assert page.locator("[data-chat-stream-content] img").count() == 0


def test_osint_source_preview_event_refetches_only_the_matching_preview(page: Page):
    requests = []
    page.route(
        "https://example.test/",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="""
              <body data-realtime-enabled="true" data-realtime-url="/sse">
                <div id="source_preview"
                     hx-get="/preview"
                     hx-trigger='realtime:osint_source.preview.finished[detail.resource.id=="source-42"] from:document'
                     hx-target="#source_preview"
                     hx-swap="outerHTML"
                     hx-select="#source_preview">
                  Waiting
                </div>
              </body>
            """,
        ),
    )
    page.route(
        "https://example.test/preview",
        lambda route: (
            requests.append(route.request.url),
            route.fulfill(status=200, content_type="text/html", body='<div id="source_preview">Preview ready</div>'),
        ),
    )
    page.goto("https://example.test/")
    page.evaluate("""
        () => {
          window.EventSource = class {
            static instances = [];

            constructor() {
              this.listeners = new Map();
              EventSource.instances.push(this);
            }

            addEventListener(type, callback) {
              const callbacks = this.listeners.get(type) || [];
              callbacks.push(callback);
              this.listeners.set(type, callbacks);
            }

            emit(type, data) {
              for (const callback of this.listeners.get(type) || []) callback({ data });
            }

            close() {}
          };
        }
    """)
    page.add_script_tag(path=str(VENDOR_JS_PATH))
    page.add_script_tag(path=str(REALTIME_JS_PATH))
    page.evaluate("() => htmx.process(document.body)")

    page.evaluate("""
        () => EventSource.instances[0].emit("message", JSON.stringify({
          pub: { data: {
            v: 1,
            type: "osint_source.preview.finished",
            change: "completed",
            resource: { kind: "osint_source", id: "source-elsewhere" },
            data: { status: "PREVIEW" },
          } },
        }))
    """)
    page.wait_for_timeout(100)
    assert requests == []

    page.evaluate("""
        () => EventSource.instances[0].emit("message", JSON.stringify({
          pub: { data: {
            v: 1,
            type: "osint_source.preview.finished",
            change: "completed",
            resource: { kind: "osint_source", id: "source-42" },
            data: { status: "PREVIEW" },
          } },
        }))
    """)
    page.locator("#source_preview").wait_for(state="visible")
    page.wait_for_function("() => document.querySelector('#source_preview')?.textContent.includes('Preview ready')")

    assert requests == ["https://example.test/preview"]


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


def test_internal_disconnect_does_not_resync_after_recovery(page: Page):
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
          source.emit("message", JSON.stringify({
            disconnect: { code: 3004, reason: "internal server error" },
          }));
          source.emit("error");
        }
    """)
    page.wait_for_function("() => EventSource.instances.length === 2")
    page.evaluate("() => EventSource.instances[1].emit('open')")
    page.wait_for_timeout(350)

    assert page.evaluate("() => window.resyncReasons") == []
    assert "hidden" in page.locator("#realtime-data-notification").get_attribute("class").split()


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


def test_htmx_refresh_in_assess(page: Page):
    _load_realtime(page, page_target="assess")
    page.evaluate("""
        () => {
          window.htmx = {
            ajax(method, url, options) {
              const refreshedAssess = document.createElement("div");
              refreshedAssess.id = "assess";
              refreshedAssess.innerHTML = `
                <div id="assess-top-bar">2 / 5 Stories</div>
                <div id="story-list">
                  <article>New story one</article>
                  <article>New story two</article>
                </div>
              `;
              document.querySelector(options.target).replaceWith(refreshedAssess);
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
    page.wait_for_function("() => document.querySelectorAll('#story-list article').length === 2")

    assert page.locator("#assess").inner_text() == "2 / 5 Stories\nNew story one\nNew story two"
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


def test_broadcast_shows_exact_persistent_message_until_dismissed(page: Page):
    _load_realtime(page)
    page.evaluate("""
        () => {
          window.broadcastTimeouts = [];
          const nativeSetTimeout = window.setTimeout.bind(window);
          window.setTimeout = (callback, delay, ...args) => {
            if (delay === 10000) window.broadcastTimeouts.push(delay);
            return nativeSetTimeout(callback, delay, ...args);
          };
        }
    """)
    page.evaluate("""
        () => EventSource.instances[0].emit("message", JSON.stringify({
          pub: {
            data: {
              v: 1,
              type: "notification.broadcast",
              change: "created",
              data: {
                message: "  Maintenance at 18:00  ",
                persistent: true,
              },
            },
          },
        }))
    """)

    notification = page.locator("[data-realtime-broadcast-notification]")
    assert notification.locator("[data-realtime-broadcast-message]").text_content() == "  Maintenance at 18:00  "

    page.wait_for_timeout(50)
    assert notification.count() == 1
    assert page.evaluate("() => window.broadcastTimeouts") == []
    notification.locator("[data-realtime-dismiss-broadcast]").click()
    assert notification.count() == 0

    page.evaluate("""
        () => EventSource.instances[0].emit("message", JSON.stringify({
          pub: {
            data: {
              v: 1,
              type: "notification.broadcast",
              data: { message: "Timed", persistent: false },
            },
          },
        }))
    """)
    assert page.evaluate("() => window.broadcastTimeouts") == [10000]
    notification.locator("[data-realtime-dismiss-broadcast]").click()


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
    assert page.evaluate("() => window.reconnectDelays") == [1000, 2000]

    page.evaluate("() => EventSource.instances[2].emit('open')")
    page.evaluate("() => EventSource.instances[2].emit('error')")
    page.wait_for_function("() => EventSource.instances.length === 4")

    assert "hidden" not in notice.get_attribute("class").split()
    assert page.evaluate("() => window.reconnectDelays") == [1000, 2000, 1000]


def test_reconnect_backoff_stops_after_eight_attempts(page: Page):
    _load_realtime(page, fast_reconnect=True)

    for expected_count in range(2, 10):
        page.evaluate("() => EventSource.instances.at(-1).emit('error')")
        page.wait_for_function(f"() => EventSource.instances.length === {expected_count}")

    page.evaluate("() => EventSource.instances.at(-1).emit('error')")
    page.wait_for_timeout(50)

    assert page.evaluate("() => EventSource.instances.length") == 9
    assert page.evaluate("() => window.reconnectDelays") == [1000, 2000, 4000, 8000, 16000, 32000, 60000, 60000]


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
