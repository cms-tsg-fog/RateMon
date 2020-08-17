FROM gitlab-registry.cern.ch/cms-cactus/ops/auto-devops/basics-c8:tag-0.0.3
# LABEL maintainer="name <email@cern.ch>"

RUN dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm && \
    dnf install -y python3 root python3-root && \
    dnf clean all