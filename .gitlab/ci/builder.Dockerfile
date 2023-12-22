FROM gitlab-registry.cern.ch/linuxsupport/alma9-base:latest
# Enable the EPEL repository
RUN dnf install epel-release -y
LABEL maintainer="Antonio Vivace <antonio.vivace@cern.ch>"

RUN yum install -y root python3-pip python3-root && \
    yum clean all && \
    pip3 install pipenv pyinstaller==4.3

# Needed to build some omsapi dependencies
RUN yum install -y krb5-devel python3-devel
# Pre-requisites for fpm
RUN yum install -y ruby ruby-devel rpm-build
# fpm and required dependencies
RUN gem install fpm json