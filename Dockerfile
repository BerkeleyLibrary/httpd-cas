FROM httpd:2.4 AS cas-build

# Build against the official image's Apache, rather than a distro Apache package.
RUN apt-get update && apt-get install -y --no-install-recommends \
        autoconf automake gcc libtool make pkg-config curl \
        libapr1-dev libaprutil1-dev libcurl4-openssl-dev libpcre2-dev libssl-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/mod_auth_cas
RUN curl -fsSL https://codeload.github.com/apereo/mod_auth_cas/tar.gz/refs/tags/v1.3 -o source.tar.gz && \
    echo "7fed6c703ba060f4eb891a9c63a0d8cf0434249bd25d1faa6b8ea9075121c93e  source.tar.gz" | sha256sum -c - && \
    tar -xzf source.tar.gz --strip-components=1 && \
    autoreconf -fi && \
    ./configure --with-apxs=/usr/local/apache2/bin/apxs && \
    make -j"$(nproc)" && make install

FROM httpd:2.4

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        libapache2-mod-auth-mellon \
        libapache2-mod-security2 \
        libcurl4t64 \
        libpcre2-8-0 \
        python3 && \
    rm -rf /var/lib/apt/lists/* && \
    install -d -o www-data -g www-data /var/cache/httpd/mod_auth_cas && \
    mkdir -p /var/www/html

COPY --from=cas-build /usr/local/apache2/modules/mod_auth_cas.so /usr/local/apache2/modules/
COPY files/etc/httpd /etc/httpd
COPY files/pre-init /usr/local/bin/pre-init
COPY --chmod=755 files/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY files/var/www /var/www
RUN ln -sf /etc/httpd/conf/httpd.conf /usr/local/apache2/conf/httpd.conf
RUN /usr/local/bin/docker-entrypoint.sh httpd -t

EXPOSE 8080
ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["httpd-foreground"]
