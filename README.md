# Apache w/mod-auth-cas docker image

The official `httpd:2.4` image with a few helpful extras:

1. mod_auth_cas, configurable at runtime by setting environment variables.
2. A RemoteIP configuration suitable for running behind NGINX, Traefik, etc.
3. Our branded auto-index pages.
4. Python3 installed for writing RewriteMap programs (and other).

Listens on 8080/tcp. Existing `/etc/httpd/conf.d/*.conf` configuration mounts
and `/var/www/html` content mounts are supported.

`mod_auth_cas` 1.3 is built from a checksum-verified upstream release against the
base image's Apache in a separate build stage. The runtime runs Apache workers
as `www-data` and initializes the existing `CAS_*` defaults through its entrypoint.
Apache modules and bundled assets live under `/usr/local/apache2`; the CAS cookie
cache remains at `/var/cache/httpd/mod_auth_cas/`.

## CAS Configuration

The CAS configuration works for localhost and auth.berkeley.edu out-of-the-box. You can override any of the options defined in [files/etc/httpd/conf.d/auth_cas.conf](files/etc/httpd/conf.d/auth_cas.conf) by setting environment variables of the form `CAS_OPTION_NAME`.

**Example 1:** Using auth-test instead of auth.

```
CAS_DOMAIN=auth-test.berkeley.edu
```

**Example 2:** Setting a production return URL.

```
CAS_ROOT_PROXIED_AS=https://mysite.lib.berkeley.edu
```

The environment variables are named after the corresponding CAS configuration directives. See the [mod-auth-cas documentation](https://github.com/apereo/mod_auth_cas). The only exception is `CAS_DOMAIN`, which is a helper variable for setting all of the other CAS URLs to a specific domain.

## Trusted Proxies

See [files/etc/httpd/conf.d/trusted_proxies.conf](files/etc/httpd/conf.d/trusted_proxies.conf) for the list of trusted proxies. This must be updated if/when a new ingress point is added.

## Branded Index Pages

This image bakes in custom branding and styling for Apache-generated index pages. See [files/var/www/autoindex](files/var/www/autoindex) for details.
