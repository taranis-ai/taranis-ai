# Taranis Ingress

The Ingress is a Nginx based on [nginxinc/nginx-unprivileged:mainline](https://hub.docker.com/r/nginxinc/nginx-unprivileged).

## Public URLs

The bundled ingress preserves the request's `Host` header, including its port.
By default it supplies its own request scheme. If an outer proxy terminates TLS,
set `TARANIS_TRUST_FORWARDED_PROTO=true` in the Compose environment or the
Kubernetes `taranis-config` ConfigMap. For Helm, set
`config.trustForwardedProto: true`. This enables scheme forwarding in both
the bundled ingress and the frontend.

With this option enabled, restrict access to the bundled ingress to the
trusted outer proxy and health probes, and keep the frontend private.
Configure the outer proxy to preserve the public `Host` and overwrite
`X-Forwarded-Proto` with a single `http` or `https` value. When using a
custom proxy directly in front of the frontend, set the same option on the
frontend only and apply those rules to its proxy.

Compose accepts `localhost` and `127.0.0.1` out of the box. For a direct
deployment on another hostname or IPv4 address, set `TARANIS_PUBLIC_HOST`.
Helm and Kustomize use the hostname from the Kubernetes Ingress. Add
aliases through the `TRUSTED_HOSTS` JSON list (Helm: `config.trustedHosts`).
The frontend includes loopback hosts for health checks and preserves
the public port when generating links.

For an existing TLS proxy, see the [Compose setup](../../docker/README.md#using-an-existing-tls-proxy).
