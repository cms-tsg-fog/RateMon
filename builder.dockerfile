FROM cern/cc7-base

RUN yum install -y ruby-devel gcc make rpm-build rubygems

RUN gem install --no-ri --no-rdoc fpm

CMD fpm
