FROM cern/cc7-base

COPY .gitlab/ci/RPMs/oracle-instantclient /oracle-rpms
COPY rpms/python36 /rpms

RUN yum install -y python3 root python36-root /oracle-rpms/*.rpm /rpms/*.rpm && \
    yum clean all && \
    rm -rf /oracle-rpms