from collections.abc import Callable
from typing import TypeVar

from playwright.sync_api import BrowserContext, Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError


HTMX_WAIT_TIMEOUT_MS = 30000
HTMX_QUIET_WINDOW_MS = 50

_HTMX_TRIGGER_SELECTOR = ", ".join(
    [
        "[hx-get]",
        "[hx-post]",
        "[hx-put]",
        "[hx-delete]",
        "[hx-patch]",
        "[hx-trigger]",
        "[hx-boost]",
        "[data-hx-get]",
        "[data-hx-post]",
        "[data-hx-put]",
        "[data-hx-delete]",
        "[data-hx-patch]",
        "[data-hx-trigger]",
        "[data-hx-boost]",
    ]
)

_HTMX_SUPPORT_SCRIPT = r"""
(() => {
  const stateName = "__taranisHtmxTestState";
  if (window[stateName]?.installed) {
    return;
  }

  const now = () => Date.now();
  const state = window[stateName] || {};
  Object.assign(state, {
    installed: true,
    pendingRequests: 0,
    lastBeforeRequest: 0,
    lastAfterRequest: 0,
    lastAfterSwap: 0,
    lastAfterSettle: 0,
    lastActivity: now(),
    lastReset: now(),
    lastError: null,
    seen: Boolean(window.htmx),
  });
  window[stateName] = state;

  const activeRequests = new WeakSet();

  const markActivity = () => {
    state.seen = true;
    state.lastActivity = now();
  };

  const requestUrl = (detail, xhr) =>
    detail?.pathInfo?.requestPath ||
    detail?.requestConfig?.path ||
    xhr?.responseURL ||
    null;

  const requestMethod = (detail) =>
    detail?.verb ||
    detail?.requestConfig?.verb ||
    detail?.requestConfig?.headers?.["HX-Request-Method"] ||
    null;

  const recordError = (event, reason) => {
    const detail = event.detail || {};
    const xhr = detail.xhr || null;
    state.lastError = {
      event: event.type,
      reason,
      method: requestMethod(detail),
      url: requestUrl(detail, xhr),
      status: xhr ? xhr.status : null,
      statusText: xhr ? xhr.statusText : null,
      timestamp: now(),
    };
    markActivity();
  };

  const startRequest = (event) => {
    const xhr = event.detail?.xhr;
    if (xhr) {
      activeRequests.add(xhr);
    }
    state.pendingRequests += 1;
    state.lastBeforeRequest = now();
    markActivity();
  };

  const finishRequest = (event) => {
    const detail = event.detail || {};
    const xhr = detail.xhr || null;
    if (xhr && activeRequests.has(xhr)) {
      activeRequests.delete(xhr);
      state.pendingRequests = Math.max(0, state.pendingRequests - 1);
    } else if (!xhr && state.pendingRequests > 0) {
      state.pendingRequests = Math.max(0, state.pendingRequests - 1);
    }

    state.lastAfterRequest = now();
    markActivity();

    if (detail.failed || detail.successful === false || (xhr && xhr.status >= 400)) {
      recordError(event, "HTMX request failed");
    }
  };

  const finishErroredRequest = (event, reason) => {
    const xhr = event.detail?.xhr;
    if (xhr && activeRequests.has(xhr)) {
      activeRequests.delete(xhr);
      state.pendingRequests = Math.max(0, state.pendingRequests - 1);
    } else if (!xhr && state.pendingRequests > 0) {
      state.pendingRequests = Math.max(0, state.pendingRequests - 1);
    }
    recordError(event, reason);
  };

  document.addEventListener("htmx:beforeRequest", startRequest, true);
  document.addEventListener("htmx:afterRequest", finishRequest, true);
  document.addEventListener("htmx:sendError", (event) => finishErroredRequest(event, "HTMX send error"), true);
  document.addEventListener("htmx:responseError", (event) => finishErroredRequest(event, "HTMX response error"), true);
  document.addEventListener("htmx:afterSwap", () => {
    state.lastAfterSwap = now();
    markActivity();
  }, true);
  document.addEventListener("htmx:afterSettle", () => {
    state.lastAfterSettle = now();
    markActivity();
  }, true);

  window.__taranisResetHtmxTestState = () => {
    state.pendingRequests = 0;
    state.lastBeforeRequest = 0;
    state.lastAfterRequest = 0;
    state.lastAfterSwap = 0;
    state.lastAfterSettle = 0;
    state.lastActivity = now();
    state.lastReset = state.lastActivity;
    state.lastError = null;
    state.seen = Boolean(window.htmx);
    return state;
  };

  window.__taranisIsHtmxSettled = (quietWindowMs) => {
    const unresolvedClasses = document.querySelector(".htmx-request, .htmx-swapping, .htmx-settling");
    if (state.pendingRequests !== 0 || unresolvedClasses) {
      return false;
    }

    return now() - state.lastActivity >= quietWindowMs;
  };
})();
"""

T = TypeVar("T")


def install_htmx_support(context: BrowserContext) -> None:
    context.add_init_script(script=_HTMX_SUPPORT_SCRIPT)


def reset_htmx_state(page: Page) -> None:
    page.evaluate("""() => window.__taranisResetHtmxTestState?.()""")


def wait_for_htmx_ready(page: Page, timeout: int = HTMX_WAIT_TIMEOUT_MS) -> None:
    page.wait_for_function(
        """selector => {
            if (window.htmx) {
                if (window.__taranisHtmxTestState) {
                    window.__taranisHtmxTestState.seen = true;
                }
                return true;
            }
            return document.readyState !== "loading" && !document.querySelector(selector);
        }""",
        arg=_HTMX_TRIGGER_SELECTOR,
        timeout=timeout,
    )


def wait_for_htmx_settled(
    page: Page,
    timeout: int = HTMX_WAIT_TIMEOUT_MS,
    quiet_window_ms: int = HTMX_QUIET_WINDOW_MS,
) -> None:
    wait_for_htmx_ready(page, timeout=timeout)
    try:
        page.wait_for_function(
            """quietWindowMs => {
                if (!window.__taranisIsHtmxSettled) {
                    return true;
                }
                return window.__taranisIsHtmxSettled(quietWindowMs);
            }""",
            arg=quiet_window_ms,
            timeout=timeout,
        )
    except PlaywrightTimeoutError as exc:
        _raise_for_recorded_htmx_error(page, exc)
        raise

    _raise_for_recorded_htmx_error(page)


def with_htmx_wait(page: Page, action: Callable[[], T], timeout: int = HTMX_WAIT_TIMEOUT_MS) -> T:
    wait_for_htmx_settled(page, timeout=timeout)
    reset_htmx_state(page)
    result = action()
    wait_for_htmx_settled(page, timeout=timeout)
    return result


def _raise_for_recorded_htmx_error(page: Page, cause: Exception | None = None) -> None:
    error = page.evaluate("""() => window.__taranisHtmxTestState?.lastError || null""")
    if not error:
        return

    method = error.get("method") or "request"
    url = error.get("url") or "unknown URL"
    status = error.get("status")
    status_text = error.get("statusText") or ""
    status_label = f" returned {status} {status_text}".rstrip() if status else ""
    message = f"{error.get('reason') or 'HTMX error'} ({error.get('event')}) for {method} {url}{status_label}"
    if cause is not None:
        raise AssertionError(message) from cause
    raise AssertionError(message)
