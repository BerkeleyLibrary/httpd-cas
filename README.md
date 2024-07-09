# Apache w/mod-auth-cas docker image

A Red Hat 8 Universal Base Image running Apache with a few helpful extras:

1. mod_auth_cas, configurable at runtime by setting environment variables.
2. A RemoteIP configuration suitable for running behind NGINX, Traefik, etc.
3. Our branded auto-index pages.

Listens on 8080/tcp.

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
