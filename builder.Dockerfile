FROM gitlab-registry.cern.ch/cms-cactus/ops/auto-devops/basics-c8:tag-0.0.3
# LABEL maintainer="name <email@cern.ch>"

RUN dnf install python3 root python36-root