FROM registry.access.redhat.com/ubi8/httpd-24

USER root
RUN yum -y update && \
    yum -y install https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
    yum -y install \
        xemacs-nox \
        mod_auth_cas \
        vim && \
    install -d -o apache /var/cache/httpd/mod_auth_cas

USER root
COPY files/etc/httpd /etc/httpd
COPY files/var/www /var/www
