/**
 * © Copyright 2018 CERN for the benefit of the CMS Collaboration
 * All rights reserved.
 *
 * @author root
 *
 * email: mail-kt@cern.ch
 */

package ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.meta;

import java.util.Arrays;
import java.util.Collection;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import ch.cern.cms.daq.oms.api.aggregation.meta.APIDataType;
import ch.cern.cms.daq.oms.api.aggregation.meta.AggregationResourceFractionMeta;
import ch.cern.cms.daq.oms.api.aggregation.meta.AggregationResourceMeta;
import ch.cern.cms.daq.oms.api.aggregation.meta.SimpleResourceMeta;
import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.Ratemon;
import ch.cern.cms.daq.oms.api.aggregation.model.exception.BadRequestActionException;
import io.katharsis.queryspec.IncludeFieldSpec;
import io.katharsis.resource.meta.DefaultPagedMetaInformation;

public class RatemonMeta extends SimpleResourceMeta  {

    public static final String RESOURCE_NAME = "subsystems.ratemon.ratemon";
    public static final String RESOURCE_PATH = "ratemon/ratemon";
    public static final String VERSION = "1.0.0";

    // <ATTRIBUTES
    public static final String ATTRIBUTE_RUNNUMBER = "runnumber";
    public static final String ATTRIBUTE_TRIGGER = "trigger";
    public static final String ATTRIBUTE_X = "x";
    public static final String ATTRIBUTE_RATE = "rate";
    public static final String ATTRIBUTE_FITS = "fits";
    public static final String ATTRIBUTE_YLABEL = "ylabel";
    public static final String ATTRIBUTE_XLABEL = "xlabel";
    // />

    public static final List<String> ATTRIBUTES = Arrays.asList(ATTRIBUTE_RUNNUMBER, ATTRIBUTE_TRIGGER, ATTRIBUTE_X, ATTRIBUTE_RATE, ATTRIBUTE_FITS, ATTRIBUTE_YLABEL, ATTRIBUTE_XLABEL);

    public static final List<String> MANDATORY_ATTRIBUTES = Arrays.asList(ATTRIBUTE_RUNNUMBER, ATTRIBUTE_TRIGGER);

    /**
     * Constructor.
     *
     * @param listFields The list of fields to be included.
     */
    public RatemonMeta(List<IncludeFieldSpec> listFields) {
        super(listFields, RESOURCE_NAME, VERSION);
        this.resourceClass = Ratemon.class;
    }

    /**
     * Constructor.
     *
     * @param listFields The list of fields to be included.
     * @param metaData   DefaultPagedMetaInformation
     */
    public RatemonMeta(List<IncludeFieldSpec> listFields, DefaultPagedMetaInformation metaData) {
        super(listFields, metaData, RESOURCE_NAME, VERSION);
        this.resourceClass = Ratemon.class;
    }

    @Override
    public Map<String, AggregationResourceMeta> fillMetadata(Collection<String> fields) {
        Map<String, AggregationResourceMeta> result = new HashMap<>();

        for (String title : fields) {
            result.put(title, getMetaForField(title));
        }

        return result;
    }

    private AggregationResourceMeta getMetaForField(String title) {
        switch (title) {
            case ATTRIBUTE_RUNNUMBER:
                return new AggregationResourceMeta("Runnumber", "NUMBER(38)", APIDataType.INTEGER, "",
                        "RUNNUMBER", "", true, true);
            case ATTRIBUTE_TRIGGER:
                return new AggregationResourceMeta("Trigger", "VARCHAR2", APIDataType.STRING, "",
                        "TRIGGER", "", true, true);
            case ATTRIBUTE_X:
                return new AggregationResourceMeta("X", "BLOB", APIDataType.STRING, "",
                        "X", "", false, false );
            case ATTRIBUTE_RATE:
                return new AggregationResourceMeta("Rate", "BLOB", APIDataType.STRING, "",
                        "RATE", "", false, false );
            case ATTRIBUTE_FITS:
                return new AggregationResourceMeta("Fits", "VARCHAR2", APIDataType.STRING, "",
                        "FITS", "", true, true);
            case ATTRIBUTE_YLABEL:
                return new AggregationResourceMeta("Ylabel", "VARCHAR2", APIDataType.STRING, "",
                        "YLABEL", "", true, true);
            case ATTRIBUTE_XLABEL:
                return new AggregationResourceMeta("Xlabel", "VARCHAR2", APIDataType.STRING, "",
                        "XLABEL", "", true, true);
            default:
                throw new BadRequestActionException(getClass().getSimpleName() + ": the '" + title
                        + "' parameter does not exists in " + RESOURCE_NAME + " resource.");
        }
    }

    @Override
    public List<String> allAttributes() {
        return ATTRIBUTES;
    }
}
