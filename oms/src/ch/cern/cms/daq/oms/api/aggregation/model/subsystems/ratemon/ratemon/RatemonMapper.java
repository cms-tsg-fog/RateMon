/**
 * © Copyright 2018 CERN for the benefit of the CMS Collaboration
 * All rights reserved.
 *
 * @author root
 *
 * email: mail-kt@cern.ch
 */

package ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.Collection;

import org.jdbi.v3.core.statement.StatementContext;

import ch.cern.cms.daq.oms.api.aggregation.base.mapper.SimpleMapper;
import ch.cern.cms.daq.oms.api.aggregation.model.exception.BadRequestActionException;
import ch.cern.cms.daq.oms.api.aggregation.model.subsystems.ratemon.ratemon.meta.RatemonMeta;
import ch.cern.cms.daq.oms.api.aggregation.utils.Converters;
import io.katharsis.queryspec.QuerySpec;

public class RatemonMapper extends SimpleMapper<Ratemon> {

    public RatemonMapper(QuerySpec querySpec) {
        super(querySpec);
    }

    @Override
    public Collection<String> getAllResourceFields() {
        return RatemonMeta.ATTRIBUTES;
    }

    @Override
    public Collection<String> generateMissingFields(Collection<String> currentAttributes) {
        return RatemonMeta.MANDATORY_ATTRIBUTES;
    }

    @Override
    public Ratemon fillResource(ResultSet rs, StatementContext ctx, Collection<String> fields) throws SQLException {
        Ratemon ratemon = new Ratemon();
        for (String field : fields) {
            switch (field) {
                // <ATTRIBUTES
                case RatemonMeta.ATTRIBUTE_RUNNUMBER:
                        ratemon.setRunnumber(Converters.getBigInteger(rs, field));
                        break;
                case RatemonMeta.ATTRIBUTE_TRIGGER:
                        ratemon.setTrigger(rs.getString(field));
                        break;
                case RatemonMeta.ATTRIBUTE_X:
                        ratemon.setX(Converters.getBlob(rs,field));
                        break;
                case RatemonMeta.ATTRIBUTE_RATE:
                        ratemon.setRate(Converters.getBlob(rs,field));
                        break;
                case RatemonMeta.ATTRIBUTE_FITS:
                        ratemon.setFits(rs.getString(field));
                        break;
                case RatemonMeta.ATTRIBUTE_YLABEL:
                        ratemon.setYlabel(rs.getString(field));
                        break;
                case RatemonMeta.ATTRIBUTE_XLABEL:
                        ratemon.setXlabel(rs.getString(field));
                        break;
                // />
                default:
                    throw new BadRequestActionException("Invalid " + this.getClass() + " title:"
                            + field + " fields:" + RatemonMeta.ATTRIBUTES.toString());
            }
        }

        ratemon.updateId();

        return ratemon;
    }
}
