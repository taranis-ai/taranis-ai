#!/usr/bin/env bash
set -euo pipefail

action="$1" root="$2" session="$3"
fail() { echo "Error: $*" >&2; exit 1; }
for window in core frontend worker; do
  tmux list-panes -t "=$session:$window" >/dev/null || fail "Start the standard development tmux session first."
done
panes=() pids=() scripts=()
snapshot="$(tmux list-panes -s -t "=$session" -F '#{window_name}|#{pane_id}|#{pane_pid}|#{pane_current_path}|#{window_panes}')"
while IFS='|' read -r window pane pid directory count; do
  case "$window" in
    core|frontend|worker) component="$window"; script=install_and_run_dev.sh ;;
    cron) component=worker; script=install_and_run_cron.sh ;;
    rq-dashboard) component=worker; script=install_and_run_rq_dashboard.sh ;;
    *) continue ;;
  esac
  [[ "$directory" == "$root/src/$component" ]] || fail "Application pane belongs to another checkout."
  [[ "$count" == 1 ]] || fail "Use one pane per application window."
  [[ "$pane" != "${TMUX_PANE:-}" ]] || fail "Run database commands outside application panes."
  panes+=("$pane"); pids+=("$pid"); scripts+=("$script")
done <<< "$snapshot"

case "$action" in
  check) exit 0 ;;
  stop)
    for pane in "${panes[@]}"; do tmux send-keys -t "$pane" C-c; done
    for _ in {1..60}; do
      busy=false
      for pid in "${pids[@]}"; do
        if pgrep -P "$pid" >/dev/null; then busy=true; fi
      done
      if ! "$busy"; then exit 0; fi
      sleep 0.5
    done
    fail "Applications did not stop; inspect their tmux panes."
    ;;
  start)
    for index in "${!panes[@]}"; do
      pgrep -P "${pids[$index]}" >/dev/null && fail "Stop applications before restarting."
      tmux send-keys -t "${panes[$index]}" C-u
      tmux send-keys -t "${panes[$index]}" -l "$4 ./${scripts[$index]}"
      tmux send-keys -t "${panes[$index]}" Enter
    done
    for _ in {1..120}; do
      sleep 1
      for pid in "${pids[@]}"; do
        pgrep -P "$pid" >/dev/null || fail "An application exited; inspect its tmux pane."
      done
      if curl --noproxy '*' -fs --max-time 1 "$5" >/dev/null &&
         curl --noproxy '*' -fs --max-time 1 "$6" >/dev/null; then exit 0; fi
    done
    fail "Applications did not become ready; inspect their tmux panes."
    ;;
  *) fail "Expected check, stop, or start." ;;
esac
