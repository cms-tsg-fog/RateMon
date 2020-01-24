# This is the dockerfile that describes the dockerimage that will be used in the
# CI/CD pipeline

## First, enable the Container Registry so you have a registry to push to.
## Build the image
# docker build --tag gitlab-registry.cern.ch/avivace/ratemon/builder --file builder.dockerfile .
## Authenticate to the CERN GitLab Registry
# docker login gitlab-registry.cern.ch
## Push the image
# docker push gitlab-registry.cern.ch/avivace/ratemon/builder

# Now, the image is available on the given GitLab registry, select it
# putting
## image: gitlab-registry.cern.ch/avivace/ratemon/builder
# in your ".gitlab-ci.yml" file, in the desired pipeline's job

FROM cern/cc7-base

RUN yum install -y git ruby-devel gcc make rpm-build rubygems

RUN gem install --no-ri --no-rdoc fpm

CMD fpm
