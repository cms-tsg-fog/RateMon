/**
 * © Copyright 2018 CERN for the benefit of the CMS Collaboration
 * All rights reserved.
 *
 * @author root
 *
 * email: mail-kt@cern.ch
 */

package ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon;

import java.math.BigDecimal;
import java.math.BigInteger;

import ch.cern.cms.daq.oms.api.aggregation.base.ResourceWithMeta;
import ch.cern.cms.daq.oms.api.aggregation.extension.annotations.Blob;
import ch.cern.cms.daq.oms.api.aggregation.extension.annotations.DateString;
import ch.cern.cms.daq.oms.api.aggregation.extension.annotations.UseSecondaryDatabase;
import ch.cern.cms.daq.oms.api.aggregation.extension.annotations.DistinctSubendpoint;
import ch.cern.cms.daq.oms.api.aggregation.meta.FindOneMeta;
import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.meta.RatemonMeta;
import io.katharsis.resource.annotations.JsonApiId;
import io.katharsis.resource.annotations.JsonApiMetaInformation;
import io.katharsis.resource.annotations.JsonApiResource;


@JsonApiResource(type = RatemonMeta.RESOURCE_PATH)
public class Ratemon implements ResourceWithMeta {

    @JsonApiId
    private String id;

    //  don't touch this tag, it's needed for later updates
    // <ATTRIBUTES
    @DistinctSubendpoint(path = "allrunnumbers")
	private BigInteger runnumber;
    @DistinctSubendpoint(path = "alltriggers")
	private String trigger;
    @Blob(path = "plot", mediaType = "image/bmp")
	private String x;
    @Blob(path = "plot", mediaType = "image/bmp")
	private String rate;
    private String fits;
    private String ylabel;
    private String xlabel;
    // />

    @JsonApiMetaInformation
    private FindOneMeta meta;

    // example only, put your own relations to other JsonApiResources here
    // @JsonApiRelation(lookUp=LookupIncludeBehavior.NONE)
    // private ResourceList<Fill> fills;  // one to many
    // private Run run;                   // one to one

    public Ratemon() {
    }


    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public void updateId() {
        setId( "" + runnumber + "_" + trigger );
    }

    public FindOneMeta getMeta() {
        return meta;
    }

    public void setMeta(FindOneMeta meta) {
        this.meta = meta;
    }

    public BigInteger getRunnumber() {
        return this.runnumber;
    }

    public void setRunnumber(BigInteger runnumber) {
        this.runnumber = runnumber;
    }

    public String getTrigger() {
        return this.trigger;
    }

    public void setTrigger(String trigger) {
        this.trigger = trigger;
    }

    public String getX() {
        return this.x;
    }

    public void setX(String x) {
        this.x = x;
    }

    public String getRate() {
        return this.rate;
    }

    public void setRate(String rate) {
        this.rate = rate;
    }

    public String getFits() {
        return this.fits;
    }

    public void setFits(String fits) {
        this.fits = fits;
    }

    public String getYlabel() {
        return this.ylabel;
    }

    public void setYlabel(String ylabel) {
        this.ylabel = ylabel;
    }

    public String getXlabel() {
        return this.xlabel;
    }

    public void setXlabel(String xlabel) {
        this.xlabel = xlabel;
    }
}
