# Apache w/mod-auth-cas docker image

A simple Debian-based Apache 2.4 image with mod-auth-cas installed. Customize the CAS configuration by setting environment variables:

- `CAS_LOGIN_URL`
- `CAS_VALIDATE_URL`
- `CAS_PROXY_VALIDATE_URL`
- `CAS_ROOT_PROXIED_AS`

The environment variables are named after the corresponding CAS configuration directives. See the [mod-auth-cas documentation](https://github.com/apereo/mod_auth_cas).
