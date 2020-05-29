ARG BASE_OS=cc7
FROM gitlab-registry.cern.ch/avivace/ratemon/oms-base:4-oms-documentation-${BASE_OS}

ENV JAVA_HOME=/opt/jdk-14
ENV PATH="$PATH:$JAVA_HOME/bin"

RUN curl -o openjdk.tar.gz https://download.java.net/java/GA/jdk14.0.1/664493ef4a6946b186ff29eb326336a2/7/GPL/openjdk-14.0.1_linux-x64_bin.tar.gz && \
    tar -C /opt -xzf openjdk.tar.gz && rm -f openjdk.tar.gz