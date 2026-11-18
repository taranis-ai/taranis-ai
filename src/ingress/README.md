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

Compose accepts loopback requests by default. Set `TRUSTED_HOSTS` to the
public hostname, or to a JSON list for multiple hostnames. Local health
checks are included automatically. Helm and Kustomize reuse the Ingress
hostname. See the [Compose setup](../../docker/README.md#using-an-existing-tls-proxy).
