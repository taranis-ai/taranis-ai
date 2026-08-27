# Three-instance collaboration demo

Add these entries to `/etc/hosts`:

```text
127.0.0.1 alpha.local.taranis.ai
127.0.0.1 bravo.local.taranis.ai
127.0.0.1 charlie.local.taranis.ai
```

Install `dev/nginx.collaboration-demo.conf` in host Nginx and reload it. The launcher never changes either privileged file.

```sh
./dev/start_collaboration_demo.sh build
./dev/start_collaboration_demo.sh up
```

Create a channel on Alpha, join it from Bravo and Charlie, edit the same story and report fields, stop Alpha, continue editing, restart it, verify equal content/version vectors, then finalize on Alpha. Use `down` to preserve databases or `reset` to remove the three demo volumes.
