/**
 * © Copyright 2018 CERN for the benefit of the CMS Collaboration
 * All rights reserved.
 *
 * @author root
 *
 * email: mail-kt@cern.ch
 */

package ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon;

import javax.ws.rs.GET;
import javax.ws.rs.Path;
import javax.ws.rs.Produces;

import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.meta.RatemonMeta;
import ch.cern.cms.daq.oms.api.aggregation.base.resourcerepository.CsvSerializableResourceRepository;
import io.katharsis.queryspec.QuerySpec;
import io.katharsis.repository.ResourceRepositoryV2;
import io.katharsis.resource.links.DefaultPagedLinksInformation;
import io.katharsis.resource.list.ResourceList;
import io.katharsis.resource.list.ResourceListBase;

@Path(RatemonMeta.RESOURCE_PATH)
public interface RatemonRepository extends CsvSerializableResourceRepository<Ratemon, String> {

    @Override
    public Ratemon findOne(String id, QuerySpec querySpec);

    @Override
    public ResourceList<Ratemon> findAll(QuerySpec querySpec);

    class RatemonList extends ResourceListBase<Ratemon, RatemonMeta, DefaultPagedLinksInformation> {
    }
}
