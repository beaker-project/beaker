FROM quay.io/centos/centos:stream9

LABEL org.opencontainers.image.source=https://github.com/beaker-project/beaker

RUN dnf install -y 'dnf-command(config-manager)' \
    && dnf config-manager --set-enabled crb \
    && dnf install -y epel-release \
    && dnf install -y \
        python3 python3-pip python3-setuptools \
        python3-sqlalchemy python3-alembic python3-daemon python3-flask \
        python3-lxml python3-six python3-markdown python3-configobj \
        python3-ldap python3-netaddr python3-passlib python3-pwquality \
        python3-rpm python3-decorator python3-itsdangerous python3-werkzeug \
        python3-requests python3-gssapi python3-simplejson python3-mysqlclient \
        python3-pytest python3-gunicorn python3-formencode \
        python3-prettytable python3-jinja2 python3-rdflib \
        mariadb openldap-servers openldap-clients lsof nss_wrapper cpio \
        createrepo_c \
    && dnf clean all
