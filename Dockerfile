ARG CI_COMMIT_REF_NAME=master
ARG CI_COMMIT_SHORT_SHA=latest
FROM gitlab-registry.cern.ch/cms-tsg-fog/ratemon/builder/alma9:latest

COPY ratemon /ratemon
WORKDIR /ratemon
RUN make

ENTRYPOINT ["/ratemon/startServer_ci.sh"]

EXPOSE 8085
