FROM gitlab-registry.cern.ch/cms-cactus/ops/auto-devops/basics-cc7:tag-0.0.8
# LABEL maintainer="name <email@cern.ch>"

COPY RPMs/oracle-instantclient /oracle-rpms

RUN yum install -y python3 root python36-root /oracle-rpms/*.rpm && \
    yum clean all && \
    pip3 install pipenv pyinstaller
