FROM gitlab-registry.cern.ch/avivace/ratemon/oms-base:cc7

COPY aggregationapi/target/aggregation*.jar /aggregator.jar
COPY aggregationapi/configuration.yml /aggregator.config.yml
COPY start.sh /start.sh

CMD ["/start.sh"]