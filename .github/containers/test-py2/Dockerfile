FROM centos:7

LABEL org.opencontainers.image.source=https://github.com/beaker-project/beaker

RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/*.repo \
    && sed -i 's/^#.*baseurl=http/baseurl=http/g' /etc/yum.repos.d/*.repo \
    && sed -i 's/^mirrorlist=http/#mirrorlist=http/g' /etc/yum.repos.d/*.repo \
    && yum install -y epel-release \
    && sed -i 's|^metalink=|#metalink=|g' /etc/yum.repos.d/epel*.repo \
    && sed -i 's|^#\?baseurl=.*|baseurl=https://archives.fedoraproject.org/pub/archive/epel/7/$basearch|g' /etc/yum.repos.d/epel*.repo

RUN printf '%s\n' \
    '[ius-vault]' \
    'name=IUS Vault for Enterprise Linux 7 - $basearch' \
    'baseurl=https://vault.ius.io/el7/$basearch/' \
    'enabled=1' \
    'gpgcheck=1' \
    'gpgkey=https://vault.ius.io/RPM-GPG-KEY-IUS-7' \
    > /etc/yum.repos.d/ius-vault.repo \
    && yum install -y git236 \
    && rm -f /etc/yum.repos.d/ius-vault.repo

RUN curl -fsSL -o /etc/yum.repos.d/beaker-server.repo https://beaker-project.org/yum/beaker-server-RedHatEnterpriseLinux.repo \
    && yum install -y mariadb beaker-integration-tests yum-utils

COPY beaker.spec /tmp/beaker.spec
RUN yum-builddep -y /tmp/beaker.spec \
    && yum remove -y beaker-common beaker-client beaker-lab-controller beaker-server beaker-integration-tests \
    && rm -f /tmp/beaker.spec \
    && yum clean all

RUN yum remove -y firefox || true \
    && yum install -y wget bzip2 \
        gtk2 gtk3 dbus-glib \
        libXt libXtst libXrender libXrandr libXfixes libXext libXdamage \
        libXcursor libXcomposite libXi libXScrnSaver libX11 \
        gdk-pixbuf2 cairo cairo-gobject pango atk \
        fontconfig freetype alsa-lib nss nspr \
        dejavu-sans-fonts dejavu-serif-fonts \
        xorg-x11-server-Xvfb \
    && wget -q https://download-installer.cdn.mozilla.net/pub/firefox/releases/43.0.4/linux-x86_64/en-US/firefox-43.0.4.tar.bz2 \
    && tar xjf firefox-43.0.4.tar.bz2 \
    && mv firefox /usr/local/firefox \
    && printf '#!/bin/sh\nexec /usr/local/firefox/firefox "$@"\n' > /usr/bin/firefox \
    && chmod +x /usr/bin/firefox \
    && ! ldd /usr/local/firefox/firefox | grep -q "not found" \
    && rm -f firefox-43.0.4.tar.bz2 \
    && yum clean all
