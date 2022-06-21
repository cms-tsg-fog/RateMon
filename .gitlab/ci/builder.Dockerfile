FROM gitlab-registry.cern.ch/cms-cactus/ops/auto-devops/basics-c8:tag-0.2.3
# LABEL maintainer="name <email@cern.ch>"

COPY RPMs/oracle-instantclient /oracle-rpms

RUN yum install -y python3 root python38-root /oracle-rpms/*.rpm && \
    yum clean all && \
    pip3 install pipenv pyinstaller==4.3
