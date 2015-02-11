#!/usr/bin/env python

import sys
import os

from selectionParser import selectionParser
import CheckPrescales
import DatabaseParser
import json
import OrderedDict

def usage():
    print sys.argv[0]+" NewJSON OldJSON OldTriggerJSONFolder"

def main():
    if len(sys.argv) < 4:
        usage()
        sys.exit(0)

    NewJSONName = sys.argv[1]
    OldJSONName = sys.argv[2]
    
    NewJSON = selectionParser(open(sys.argv[1]).read()).runsandls()
    OldJSON = selectionParser(open(sys.argv[2]).read()).runsandls()

    TrigFolder  = sys.argv[3]

    KeyQuery = """
    SELECT A.TRIGGERMODE, B.HLT_KEY, B.GT_RS_KEY, B.TSC_KEY, C.CONFIGID, D.GT_KEY FROM
    CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF B, CMS_HLT.CONFIGURATIONS C, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
    B.ID = A.TRIGGERMODE AND C.CONFIGDESCRIPTOR = B.HLT_KEY AND D.TS_Key = B.TSC_Key AND A.RUNNUMBER=%d
    """

    JSONS = {}
    for run in sorted(NewJSON.iterkeys()):
        if OldJSON.has_key(run):
            continue  # skip already processed runs
        LSs = NewJSON[run]
        print "Processing Run: %d" % (run,)
        parser = DatabaseParser.DatabaseParser()
        parser.RunNumber = run
        parser.ParseRunSetup()
        
        PrescaleTable = CheckPrescales.GetPrescaleTable(parser.HLT_Key,parser.GT_Key,parser.GTRS_Key,[],False)

        for HLT,Prescales in PrescaleTable.iteritems():            
            HLTNoV = DatabaseParser.StripVersion(HLT)
            oldpath = TrigFolder + "/" + HLTNoV + "_" + OldJSONName
            if not JSONS.has_key(HLTNoV):
                if os.path.exists(oldpath):
                    JSONS[HLTNoV] = json.load(open(oldpath))
                else:
                    JSONS[HLTNoV] = {}
            tmpLSRange = []
            for ls in LSs:                
                if Prescales[parser.PSColumnByLS[ls]] == 1:
                    tmpLSRange.append(ls)
            JSONS[HLTNoV][str(run)] = truncateRange(tmpLSRange)
    if not os.path.exists(TrigFolder):
        os.system("mkdir -p %s" % (TrigFolder,))
    for name in JSONS.iterkeys():
        thisJSON = JSONS[name]
        sortedJSON = OrderedDict.OrderedDict()
        for key in sorted(thisJSON.iterkeys()):
            sortedJSON[key] = thisJSON[key]
        newpath = TrigFolder + "/" + DatabaseParser.StripVersion(name) + "_" + NewJSONName
        #print "Writing %s" % (newpath,)
        out = open(newpath,'w')
        out.write(json.dumps(sortedJSON))
        #out.write(str(oldJSON))
        out.close()
        
        
def truncateRange(inp):
    if len(inp)==0:
        return []
    start = inp[0]
    out = []
    for i in range(len(inp)):
        if i==0: continue # skip the first entry
        if not inp[i] == inp[i-1]+1:
            out.append([start,inp[i-1]])
            start = inp[i]           
    out.append([start,inp[-1]])
    return out
              


if __name__=='__main__':
    main()
    
