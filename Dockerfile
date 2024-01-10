FROM httpd:2.4

RUN apt -y update && \
    apt -y upgrade && \
    apt -y install libapache2-mod-auth-cas && \
    install -d /var/cache/apache2/mod_auth_cas -o www-data -g www-data

COPY httpd.conf /usr/local/apache2/conf/httpd.conf

VOLUME [ "/var/cache/apache2/mod_auth_cas" ]
