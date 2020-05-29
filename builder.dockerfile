ARG BASE_OS=cc7
ARG BASE_TAG
FROM cern/${BASE_OS}-base:${BASE_TAG}
# LABEL maintainer="name <email@cern.ch>"

RUN yum install -y git ruby-devel gcc make rpm-build rubygems && \
    yum clean all

RUN gem install --no-ri --no-rdoc fpm

CMD fpm
