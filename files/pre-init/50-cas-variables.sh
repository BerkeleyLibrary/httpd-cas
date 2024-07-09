# For option definitions:
# @see https://github.com/apereo/mod_auth_cas

# Special helper variable that allows setting all the CAS URLs at once.
export CAS_DOMAIN=${CAS_DOMAIN:-auth.berkeley.edu}

export CAS_CACHE_CLEAN_INTERVAL="${CAS_CACHE_CLEAN_INTERVAL:-1800}"
export CAS_COOKIE_ENTROPY="${CAS_COOKIE_ENTROPY:-32}"
export CAS_COOKIE_PATH="${CAS_COOKIE_PATH:-/var/cache/httpd/mod_auth_cas/}"
export CAS_DEBUG="${CAS_DEBUG:-off}"
export CAS_IDLE_TIMEOUT="${CAS_IDLE_TIMEOUT:-3600}"
export CAS_LOGIN_URL="${CAS_LOGIN_URL:-https://$CAS_DOMAIN/cas/}"
export CAS_PROXY_VALIDATE_URL="${CAS_PROXY_VALIDATE_URL:-https://$CAS_DOMAIN/cas/proxyValidate}"
export CAS_ROOT_PROXIED_AS="${CAS_ROOT_PROXIED_AS:-http://localhost}"
export CAS_TIMEOUT="${CAS_TIMEOUT:-7200}"
export CAS_VALIDATE_URL="${CAS_VALIDATE_URL:-https://$CAS_DOMAIN/cas/serviceValidate}"
export CAS_VERSION="${CAS_VERSION:-2}"
