FROM gitlab-registry.cern.ch/cms-cactus/ops/auto-devops/basics-cc7:tag-0.0.3
# LABEL maintainer="name <email@cern.ch>"

RUN yum install -y python3 root python36-root && \
    yum clean all