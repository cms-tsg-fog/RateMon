# from Ulf: OMS will run on CC7 during run 3
ARG BASE_OS=cc7
ARG BASE_TAG
FROM cern/${BASE_OS}-base:${BASE_TAG}
# LABEL maintainer="name <email@cern.ch>"

RUN yum install -y git net-tools openssl gcc-c++ make \
  /oracle-rpms/oracle-instantclient-tnsnames.ora-12.1-4.noarch.rpm \
  /oracle-rpms/oracle-instantclient-12.1-10.el7.cern.x86_64.rpm \
  /oracle-rpms/oracle-instantclient12.1-basic-12.1.0.2.0-1.x86_64.rpm \
  /oracle-rpms/oracle-instantclient12.1-meta-12.1-10.el7.cern.x86_64.rpm && \
  yum clean all