FROM gitlab-registry.cern.ch/cms-tsg-fog/ratemon/oms-base:cc7

COPY aggregationapi/target/aggregation*.jar /aggregator.jar
COPY configuration.yml /aggregator.config.yml
COPY start.sh /start.sh

CMD ["/start.sh"]
EXPOSE 80