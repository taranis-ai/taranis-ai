# Collaboration Demo Setup

Use this setup when running multiple local Taranis instances on one machine and you want collaboration links to use stable hostnames instead of `localhost:<port>`.

## `/etc/hosts`

Add:

```text
127.0.0.1 alpha.local.taranis.ai
127.0.0.1 bravo.local.taranis.ai
```

## Host nginx

Install the sample config:

```bash
sudo cp dev/nginx.collaboration-demo.conf /etc/nginx/sites-available/taranis-collaboration-demo
sudo ln -s /etc/nginx/sites-available/taranis-collaboration-demo /etc/nginx/sites-enabled/taranis-collaboration-demo
sudo nginx -t && sudo systemctl reload nginx
```

The sample config routes:

- `http://alpha.local.taranis.ai` -> local Taranis ingress on `127.0.0.1:8081`
- `http://bravo.local.taranis.ai` -> local Taranis ingress on `127.0.0.1:8082`

## Start the demo

Use the provided launcher:

```bash
chmod +x dev/start_collaboration_demo.sh
./dev/start_collaboration_demo.sh up
```

Useful commands:

```bash
./dev/start_collaboration_demo.sh status
./dev/start_collaboration_demo.sh logs alpha
./dev/start_collaboration_demo.sh logs bravo
./dev/start_collaboration_demo.sh down
```

The launcher uses:

- `docker/.env.stack1`
- `docker/.env.stack2`

and starts two distinct Compose projects:

- `taranis-stack1`
- `taranis-stack2`

You can override the env file paths when needed:

```bash
ALPHA_ENV=/path/to/.env.stack1 BRAVO_ENV=/path/to/.env.stack2 ./dev/start_collaboration_demo.sh up
```

## Expected collaboration flow

Create the channel on:

- `http://alpha.local.taranis.ai/frontend`

The invite should embed:

- `owner_base_url=http://alpha.local.taranis.ai`

Redeem the same invite on:

- `http://bravo.local.taranis.ai/frontend/collaboration/join?...`

Do not prepend another `/frontend`. The generated invite path already includes it.
