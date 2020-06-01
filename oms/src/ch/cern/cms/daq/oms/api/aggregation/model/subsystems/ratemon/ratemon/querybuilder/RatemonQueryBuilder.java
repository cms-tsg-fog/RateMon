/**
 * © Copyright 2018 CERN for the benefit of the CMS Collaboration
 * All rights reserved.
 *
 * @author root
 *
 * email: mail-kt@cern.ch
 */

package ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.querybuilder;

import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.meta.RatemonMeta;
import ch.cern.cms.daq.oms.api.aggregation.utils.querybuilderv2.QueryBuilderV2;
import ch.cern.cms.daq.oms.api.aggregation.utils.querybuilderv2.table.QueryTableMaster;
import ch.cern.cms.daq.oms.api.aggregation.utils.sql.FilterOperatorToOracle;

public class RatemonQueryBuilder extends QueryBuilderV2 {
    public RatemonQueryBuilder() {
        super(RatemonMeta.RESOURCE_NAME);

        masterTable = new QueryTableMaster("CMS_TRG_L1_MON.RATEMON", "C");

        addIdentifyingAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_RUNNUMBER)
                    .forColumn("RUNNUMBER")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_NUMBER));

        addIdentifyingAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_TRIGGER)
                    .forColumn("TRIGGER")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_STRING));

        addAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_X)
                    .forColumn("X")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_STRING));

        addAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_RATE)
                    .forColumn("RATE")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_STRING));

        addAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_FITS)
                    .forColumn("FITS")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_STRING));

        addAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_YLABEL)
                    .forColumn("YLABEL")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_STRING));

        addAttribute(masterTable.attributeNamed(RatemonMeta.ATTRIBUTE_XLABEL)
                    .forColumn("XLABEL")
                    .convertingAs(FilterOperatorToOracle.CONVERSION_STRING));
    }
}
