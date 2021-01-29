FROM gitlab-registry.cern.ch/cms-cactus/ops/auto-devops/basics-cc7:tag-0.0.7
# LABEL maintainer="name <email@cern.ch>"

COPY RPMs/oracle-instantclient /oracle-rpms

RUN yum install -y python3 root python36-root /oracle-rpms/*.rpm && \
    yum clean all && \
    pip3 install pipenv pyinstaller altgraph appdirs certfif distlib filelock importlib-metadata importlib-resources six virtualenv virtualenv-clone zipp 