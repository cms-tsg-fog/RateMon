/**
 * © Copyright 2018 CERN for the benefit of the CMS Collaboration
 * All rights reserved.
 *
 * @author root
 *
 * email: mail-kt@cern.ch
 */

package ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon;

import java.util.ArrayList;

import javax.inject.Inject;

import ch.cern.cms.daq.oms.api.aggregation.base.resourcerepository.QueryBuilderResourceRepository;
import ch.cern.cms.daq.oms.api.aggregation.managed.AggregationManaged;
import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.meta.RatemonMeta;
import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.querybuilder.RatemonQueryBuilder;
import ch.cern.cms.daq.oms.api.aggregation.utils.json.MetadataFormatter;
import ch.cern.cms.daq.oms.api.aggregation.utils.sql.QueryBuilderInterface;
import io.katharsis.queryspec.QuerySpec;

public class RatemonRepositoryImpl extends QueryBuilderResourceRepository<Ratemon, String>
        implements RatemonRepository {
    private RatemonQueryBuilder queryBuilder = new RatemonQueryBuilder();

    public RatemonRepositoryImpl() {
        super(Ratemon.class);
    }

    @Inject
    public RatemonRepositoryImpl(AggregationManaged aggregationManaged) {
        super(Ratemon.class, aggregationManaged);
    }

    @Override
    public QueryBuilderInterface getQueryBuilder() {
        return queryBuilder;
    }

    @Override
    protected void fillQueryWithId(String id, QuerySpec querySpec) {
        // FIXME: Unimplemented method
    }

    @Override
    public boolean isQueryPaginationEnabled() {
        return true;
    }
}
