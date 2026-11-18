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

Set `TRUSTED_HOSTS` to a JSON list such as
`["taranis.example.org","localhost","127.0.0.1"]` to enable hostname
validation. Helm accepts the list in `config.trustedHosts`. Include the
public names and the loopback names used by the health probes. Flask
validates the hostname independently of the port.
