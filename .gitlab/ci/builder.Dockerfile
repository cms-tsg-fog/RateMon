FROM gitlab-registry.cern.ch/linuxsupport/alma9-base:latest
# Enable the EPEL repository
RUN dnf install epel-release -y
# LABEL maintainer="name <email@cern.ch>"

RUN yum install -y root krb5-devel python3-devel python3-pip python3-root && \
    yum clean all && \
    pip3 install pipenv pyinstaller==4.3
