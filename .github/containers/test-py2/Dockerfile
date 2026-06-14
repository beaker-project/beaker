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
