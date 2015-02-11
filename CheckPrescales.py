#!/usr/bin/env python

import sys
import os
import getopt
import copy

from DatabaseParser import ConnectDB

def usage():
    print sys.argv[0] + " [options] HLTKey GTKey GTRS Key"
    print "options:"
    print "-v                 Verbose Mode"
    print "--ignore=<cols>    list (comma-separated) of prescale columns to ignore"

def main():
    try:
        opt, args = getopt.getopt(sys.argv[1:],"v",["ignore="])
        
    except getopt.GetoptError, err:
        print str(err)
        usage()
        sys.exit(2)

    if len(args)!=3:
        usage()
        sys.exit(0)

    HLT_Key  = args[0]
    GT_Key   = args[1]
    GTRS_Key = args[2]
    Verbose = False
    PSColsToIgnore = []

    for o,a in opt:
        if o=="-v":
            Verbose = True
        elif o=="--ignore":            
            for c in a.split(','):
                try:
                    PSColsToIgnore.append(int(c))
                except:
                    print "\nERROR: %s is not a valid prescale column\n" % c
                    usage()
                    sys.exit(0)
    psTable = GetPrescaleTable(HLT_Key,GT_Key,GTRS_Key,PSColsToIgnore,True)

    if Verbose:
        firstPS = {}
        for trigger,prescales in psTable.iteritems():
            firstPed = firstPrescaled(prescales,PSColsToIgnore)
            if not firstPS.has_key(firstPed):
                firstPS[firstPed] = []
            firstPS[firstPed].append(trigger)

           
        for col,triggers in firstPS.iteritems():
            if col == -1:
                print "The following triggers are never prescaled:"
            else:
                print "The following triggers are first prescaled in col %d" % (col,)
            for trig in triggers: print "\t%s" % (trig,)
               
            
            
def GetPrescaleTable(HLT_Key,GT_Key,GTRS_Key,PSColsToIgnore,doPrint):
    curs = ConnectDB('hlt')

    ## Get the HLT seeds
    sqlquery ="""  
    SELECT I.NAME,A.VALUE
    FROM
    CMS_HLT.STRINGPARAMVALUES A,
    CMS_HLT.PARAMETERS B,
    CMS_HLT.SUPERIDPARAMETERASSOC C,
    CMS_HLT.MODULETEMPLATES D,
    CMS_HLT.MODULES E,
    CMS_HLT.PATHMODULEASSOC F,
    CMS_HLT.CONFIGURATIONPATHASSOC G,
    CMS_HLT.CONFIGURATIONS H,
    CMS_HLT.PATHS I
    WHERE
    A.PARAMID = C.PARAMID AND
    B.PARAMID = C.PARAMID AND
    B.NAME = 'L1SeedsLogicalExpression' AND
    C.SUPERID = F.MODULEID AND
    D.NAME = 'HLTLevel1GTSeed' AND
    E.TEMPLATEID = D.SUPERID AND
    F.MODULEID = E.SUPERID AND
    F.PATHID=G.PATHID AND
    I.PATHID=G.PATHID AND
    G.CONFIGID=H.CONFIGID AND
    H.CONFIGDESCRIPTOR='%s' 
    ORDER BY A.VALUE
        """ % (HLT_Key,)
    curs.execute(sqlquery)
    HLTSeed = {}
    for HLTPath,L1Seed in curs.fetchall():
        if not HLTSeed.has_key(HLTPath): ## this should protect us from L1_SingleMuOpen
            tmp = L1Seed.lstrip('"').rstrip('"') 
            HLTSeed[HLTPath] = tmp.rstrip(' ')
            
    HLTPrescales = GetHLTPrescaleMatrix(curs,HLT_Key)

    L1Names = {}
    ## get the L1 algo names associated with each algo bit
    AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
    WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
    ORDER BY ALGO_INDEX""" % (GT_Key,)
    curs.execute(AlgoNameQuery)
    for index,name in curs.fetchall():
        L1Names[name] = index

    L1Prescales = GetL1AlgoPrescales(curs,GTRS_Key)

    FullPrescales = {}
    formatString = "hlt path: %s\nl1t seed: %s\ntotal p.: %s\nhlt pre.: %s\nl1t pre.: %s\n"
    if doPrint:
        print "List of triggers with non-sequential prescales:"
        #print formatString % ("HLT Name","L1 Name","Total","HLT","L1",)
    for HLTName,L1Seeds in HLTSeed.iteritems():
        if HLTName.startswith('AlCa'): ## the results don't make sense for AlCa paths
            continue
        if L1Seeds.isdigit():  ## skip TT seeded paths
            continue
        thisL1PS = []
        for seed in L1Seeds.split(' OR '): ## unwind the OR of multiple seeds
            seed = seed.lstrip(' ').rstrip(' ')
            if seed.isdigit():
                continue
            if not L1Names.has_key(seed):
                print "WARNING: %s uses non-existant L1 seed: %s" % (HLTName,seed,)
            tmp = L1Prescales[L1Names[seed]]
            if len(thisL1PS)==0:
                thisL1PS = copy.copy(tmp) ## just set it for the first one
            else:
                for i,a,b in zip(range(len(tmp)),thisL1PS,tmp):
                    if b<a:
                        thisL1PS[i] = b # choose the minimum PS for each column
        if len(thisL1PS)==0:
            continue  ## this probably means that the seeding was an OR of TTs
        if HLTPrescales.has_key(HLTName):   ## if the HLT path is totally unprescaled it won't be listed in the PS service
            thisHLTPS = HLTPrescales[HLTName]
        else:
            thisHLTPS = [1]*len(thisL1PS)
        if not len(thisHLTPS) == len(thisL1PS):
            print "Incompatible number of prescales columns for trigger %s" % HLTName
            continue
        prescales = []
        for hlt,l1 in zip(thisHLTPS,thisL1PS):
            prescales.append(hlt*l1)
        #print HLTName+" HLT: "+str(thisHLTPS)+" L1: "+str(thisL1PS)+" Total: "+str(prescales)
        if not isSequential(prescales,PSColsToIgnore) and doPrint:
            print formatString % (HLTName,L1Seeds,prescales,thisHLTPS,thisL1PS,)
        FullPrescales[HLTName] = prescales
    return FullPrescales
            
def GetHLTPrescaleMatrix(cursor,HLT_Key):
    ## Get the config ID
    configIDQuery = "SELECT CONFIGID FROM CMS_HLT.CONFIGURATIONS WHERE CONFIGDESCRIPTOR='%s'" % (HLT_Key,)
    cursor.execute(configIDQuery)
    ConfigId, = cursor.fetchone()

    SequencePathQuery ="""
    SELECT F.SEQUENCENB,J.VALUE TRIGGERNAME
    FROM CMS_HLT.CONFIGURATIONSERVICEASSOC A
    , CMS_HLT.SERVICES B
    , CMS_HLT.SERVICETEMPLATES C
    , CMS_HLT.SUPERIDVECPARAMSETASSOC D
    , CMS_HLT.VECPARAMETERSETS E
    , CMS_HLT.SUPERIDPARAMSETASSOC F
    , CMS_HLT.PARAMETERSETS G
    , CMS_HLT.SUPERIDPARAMETERASSOC H
    , CMS_HLT.PARAMETERS I
    , CMS_HLT.STRINGPARAMVALUES J
    WHERE A.CONFIGID= %d
    AND A.SERVICEID=B.SUPERID
    AND B.TEMPLATEID=C.SUPERID
    AND C.NAME='PrescaleService'
    AND B.SUPERID=D.SUPERID
    AND D.VPSETID=E.SUPERID
    AND E.NAME='prescaleTable'
    AND D.VPSETID=F.SUPERID
    AND F.PSETID=G.SUPERID
    AND G.SUPERID=H.SUPERID
    AND I.PARAMID=H.PARAMID
    AND I.NAME='pathName'
    AND J.PARAMID=H.PARAMID
    ORDER BY F.SEQUENCENB
    """ % (ConfigId,)

    cursor.execute(SequencePathQuery)
    HLTSequenceMap = {}
    for seq,name in cursor.fetchall():
        name = name.lstrip('"').rstrip('"')
        HLTSequenceMap[seq]=name

    SequencePrescaleQuery="""
    SELECT F.SEQUENCENB,J.SEQUENCENB,J.VALUE
    FROM CMS_HLT.CONFIGURATIONSERVICEASSOC A
    , CMS_HLT.SERVICES B
    , CMS_HLT.SERVICETEMPLATES C
    , CMS_HLT.SUPERIDVECPARAMSETASSOC D
    , CMS_HLT.VECPARAMETERSETS E
    , CMS_HLT.SUPERIDPARAMSETASSOC F
    , CMS_HLT.PARAMETERSETS G
    , CMS_HLT.SUPERIDPARAMETERASSOC H
    , CMS_HLT.PARAMETERS I
    , CMS_HLT.VUINT32PARAMVALUES J
    WHERE A.CONFIGID=%d 
    AND A.SERVICEID=B.SUPERID
    AND B.TEMPLATEID=C.SUPERID
    AND C.NAME='PrescaleService'
    AND B.SUPERID=D.SUPERID
    AND D.VPSETID=E.SUPERID
    AND E.NAME='prescaleTable'
    AND D.VPSETID=F.SUPERID
    AND F.PSETID=G.SUPERID
    AND G.SUPERID=H.SUPERID
    AND I.PARAMID=H.PARAMID
    AND I.NAME='prescales'
    AND J.PARAMID=H.PARAMID
    ORDER BY F.SEQUENCENB,J.SEQUENCENB
    """ % (ConfigId,)

    #print HLTSequenceMap
    cursor.execute(SequencePrescaleQuery)
    HLTPrescaleTable= {}
    lastIndex=-1
    lastSeq=-1
    row = []
    for seq,index,val in cursor.fetchall():
        if lastIndex!=index-1:
            HLTPrescaleTable[HLTSequenceMap[seq-1]] = row
            row=[]
        lastSeq=seq
        lastIndex=index
        row.append(val)

    return HLTPrescaleTable

def GetL1AlgoPrescales(curs, GTRS_Key):
    L1PrescalesQuery= """
    SELECT
    PRESCALE_FACTOR_ALGO_000,PRESCALE_FACTOR_ALGO_001,PRESCALE_FACTOR_ALGO_002,PRESCALE_FACTOR_ALGO_003,PRESCALE_FACTOR_ALGO_004,PRESCALE_FACTOR_ALGO_005,
    PRESCALE_FACTOR_ALGO_006,PRESCALE_FACTOR_ALGO_007,PRESCALE_FACTOR_ALGO_008,PRESCALE_FACTOR_ALGO_009,PRESCALE_FACTOR_ALGO_010,PRESCALE_FACTOR_ALGO_011,
    PRESCALE_FACTOR_ALGO_012,PRESCALE_FACTOR_ALGO_013,PRESCALE_FACTOR_ALGO_014,PRESCALE_FACTOR_ALGO_015,PRESCALE_FACTOR_ALGO_016,PRESCALE_FACTOR_ALGO_017,
    PRESCALE_FACTOR_ALGO_018,PRESCALE_FACTOR_ALGO_019,PRESCALE_FACTOR_ALGO_020,PRESCALE_FACTOR_ALGO_021,PRESCALE_FACTOR_ALGO_022,PRESCALE_FACTOR_ALGO_023,
    PRESCALE_FACTOR_ALGO_024,PRESCALE_FACTOR_ALGO_025,PRESCALE_FACTOR_ALGO_026,PRESCALE_FACTOR_ALGO_027,PRESCALE_FACTOR_ALGO_028,PRESCALE_FACTOR_ALGO_029,
    PRESCALE_FACTOR_ALGO_030,PRESCALE_FACTOR_ALGO_031,PRESCALE_FACTOR_ALGO_032,PRESCALE_FACTOR_ALGO_033,PRESCALE_FACTOR_ALGO_034,PRESCALE_FACTOR_ALGO_035,
    PRESCALE_FACTOR_ALGO_036,PRESCALE_FACTOR_ALGO_037,PRESCALE_FACTOR_ALGO_038,PRESCALE_FACTOR_ALGO_039,PRESCALE_FACTOR_ALGO_040,PRESCALE_FACTOR_ALGO_041,
    PRESCALE_FACTOR_ALGO_042,PRESCALE_FACTOR_ALGO_043,PRESCALE_FACTOR_ALGO_044,PRESCALE_FACTOR_ALGO_045,PRESCALE_FACTOR_ALGO_046,PRESCALE_FACTOR_ALGO_047,
    PRESCALE_FACTOR_ALGO_048,PRESCALE_FACTOR_ALGO_049,PRESCALE_FACTOR_ALGO_050,PRESCALE_FACTOR_ALGO_051,PRESCALE_FACTOR_ALGO_052,PRESCALE_FACTOR_ALGO_053,
    PRESCALE_FACTOR_ALGO_054,PRESCALE_FACTOR_ALGO_055,PRESCALE_FACTOR_ALGO_056,PRESCALE_FACTOR_ALGO_057,PRESCALE_FACTOR_ALGO_058,PRESCALE_FACTOR_ALGO_059,
    PRESCALE_FACTOR_ALGO_060,PRESCALE_FACTOR_ALGO_061,PRESCALE_FACTOR_ALGO_062,PRESCALE_FACTOR_ALGO_063,PRESCALE_FACTOR_ALGO_064,PRESCALE_FACTOR_ALGO_065,
    PRESCALE_FACTOR_ALGO_066,PRESCALE_FACTOR_ALGO_067,PRESCALE_FACTOR_ALGO_068,PRESCALE_FACTOR_ALGO_069,PRESCALE_FACTOR_ALGO_070,PRESCALE_FACTOR_ALGO_071,
    PRESCALE_FACTOR_ALGO_072,PRESCALE_FACTOR_ALGO_073,PRESCALE_FACTOR_ALGO_074,PRESCALE_FACTOR_ALGO_075,PRESCALE_FACTOR_ALGO_076,PRESCALE_FACTOR_ALGO_077,
    PRESCALE_FACTOR_ALGO_078,PRESCALE_FACTOR_ALGO_079,PRESCALE_FACTOR_ALGO_080,PRESCALE_FACTOR_ALGO_081,PRESCALE_FACTOR_ALGO_082,PRESCALE_FACTOR_ALGO_083,
    PRESCALE_FACTOR_ALGO_084,PRESCALE_FACTOR_ALGO_085,PRESCALE_FACTOR_ALGO_086,PRESCALE_FACTOR_ALGO_087,PRESCALE_FACTOR_ALGO_088,PRESCALE_FACTOR_ALGO_089,
    PRESCALE_FACTOR_ALGO_090,PRESCALE_FACTOR_ALGO_091,PRESCALE_FACTOR_ALGO_092,PRESCALE_FACTOR_ALGO_093,PRESCALE_FACTOR_ALGO_094,PRESCALE_FACTOR_ALGO_095,
    PRESCALE_FACTOR_ALGO_096,PRESCALE_FACTOR_ALGO_097,PRESCALE_FACTOR_ALGO_098,PRESCALE_FACTOR_ALGO_099,PRESCALE_FACTOR_ALGO_100,PRESCALE_FACTOR_ALGO_101,
    PRESCALE_FACTOR_ALGO_102,PRESCALE_FACTOR_ALGO_103,PRESCALE_FACTOR_ALGO_104,PRESCALE_FACTOR_ALGO_105,PRESCALE_FACTOR_ALGO_106,PRESCALE_FACTOR_ALGO_107,
    PRESCALE_FACTOR_ALGO_108,PRESCALE_FACTOR_ALGO_109,PRESCALE_FACTOR_ALGO_110,PRESCALE_FACTOR_ALGO_111,PRESCALE_FACTOR_ALGO_112,PRESCALE_FACTOR_ALGO_113,
    PRESCALE_FACTOR_ALGO_114,PRESCALE_FACTOR_ALGO_115,PRESCALE_FACTOR_ALGO_116,PRESCALE_FACTOR_ALGO_117,PRESCALE_FACTOR_ALGO_118,PRESCALE_FACTOR_ALGO_119,
    PRESCALE_FACTOR_ALGO_120,PRESCALE_FACTOR_ALGO_121,PRESCALE_FACTOR_ALGO_122,PRESCALE_FACTOR_ALGO_123,PRESCALE_FACTOR_ALGO_124,PRESCALE_FACTOR_ALGO_125,
    PRESCALE_FACTOR_ALGO_126,PRESCALE_FACTOR_ALGO_127
    FROM CMS_GT.GT_FDL_PRESCALE_FACTORS_ALGO A, CMS_GT.GT_RUN_SETTINGS_PRESC_VIEW B
    WHERE A.ID=B.PRESCALE_FACTORS_ALGO_FK AND B.ID='%s'
    """ % (GTRS_Key,)
    curs.execute(L1PrescalesQuery)
    ## This is pretty horrible, but this how you get them!!
    tmp = curs.fetchall()
    L1PrescaleTable = []
    for ps in tmp[0]: #build the prescale table initially
        L1PrescaleTable.append([ps])
    for line in tmp[1:]: # now fill it
        for ps,index in zip(line,range(len(line))):
            L1PrescaleTable[index].append(ps)
    return L1PrescaleTable

def isSequential(row,ignore):
    seq = True
    lastEntry=999999999999
    for i,entry in enumerate(row):
        if i in ignore:
            continue
        if entry > lastEntry and lastEntry!=0:
            seq = False
            break
        lastEntry = entry
    return seq


def firstPrescaled(row,ignore):
    row.reverse()
    for i,val in enumerate(row):
        if len(row)-1-i in ignore:
            continue
        if val!=1: # prescaled
            return len(row)-1-i
    return -1

if __name__=='__main__':
    main()
