ARG CI_COMMIT_REF_NAME=master
ARG CI_COMMIT_SHORT_SHA=latest
FROM gitlab-registry.cern.ch/cms-tsg-fog/ratemon/builder:${CI_COMMIT_REF_NAME}-${CI_COMMIT_SHORT_SHA}

COPY ratemon /ratemon
WORKDIR /ratemon
RUN make

ENTRYPOINT ["python3", "server.py"]

EXPOSE 8085