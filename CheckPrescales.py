#!/usr/bin/env python

import sys
import os
import getopt
import copy

#import pdb

import xml.etree.ElementTree
from DatabaseParser import ConnectDB

def usage():
    print sys.argv[0] + " [options] HLTKey uGTKey RS Key"
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
    uGT_Key   = args[1]
    RS_Key = args[2]
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
    psTable = GetPrescaleTable(HLT_Key,uGT_Key,RS_Key,PSColsToIgnore,True)

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
               
            
            
def GetPrescaleTable(HLT_Key,uGT_Key,RS_Key,PSColsToIgnore,doPrint):
    curs = ConnectDB('hlt')
    trg_curs = ConnectDB()
    ## Get the HLT seeds
    sqlquery ="""  
    select l.name as path, e.value 
    from
    cms_hlt_gdr.u_confversions a, 
    cms_hlt_gdr.u_pathid2conf b, 
    cms_hlt_gdr.u_pathid2pae c, 
    cms_hlt_gdr.u_pae2moe d,  
    cms_hlt_gdr.u_moelements e, 
    cms_hlt_gdr.u_moduletemplates f, 
    cms_hlt_gdr.u_mod2templ g, 
    cms_hlt_gdr.u_pathids h, 
    cms_hlt_gdr.u_paths l
    where
    a.name='%s' and
    b.id_confver=a.id and
    c.id_pathid=b.id_pathid and
    h.id=b.id_pathid and
    l.id=h.id_path and
    g.id_pae=c.id_pae and
    d.id_pae=c.id_pae and
    e.id=d.id_moe and
    f.id=g.id_templ and
    f.name= 'HLTL1TSeed' and 
    e.name='L1SeedsLogicalExpression'
    order by e.value
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
    AlgoNameQuery = """select D.CONF from CMS_TRG_L1_CONF.UGT_L1_MENU D, CMS_TRG_L1_CONF.UGT_KEYS A WHERE D.ID=A.L1_MENU AND A.ID='%s'""" % (uGT_Key)
    trg_curs.execute(AlgoNameQuery)
    
    l1xml = trg_curs.fetchall()[0][0].read()
    e = xml.etree.ElementTree.fromstring(l1xml)
    for r in e.findall('algorithm'):
        name = r.find('name').text.replace(' ','')
        index = int(r.find('index').text.replace(' ',''))
        L1Names[name] = index
    L1Prescales = GetL1AlgoPrescales(trg_curs,RS_Key)

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
            else:
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
#        if L1Seeds == 'L1_ZeroBias': pdb.set_trace()
        for hlt,l1 in zip(thisHLTPS,thisL1PS):
           prescales.append(int(hlt)*int(l1))

        #print HLTName+" HLT: "+str(thisHLTPS)+" L1: "+str(thisL1PS)+" Total: "+str(prescales)
        if not isSequential(prescales,PSColsToIgnore) and doPrint:
            print formatString % (HLTName,L1Seeds,prescales,thisHLTPS,thisL1PS,)
        FullPrescales[HLTName] = prescales
    return FullPrescales
            
def GetHLTPrescaleMatrix(cursor,HLT_Key):
    ## Get the config ID
    configIDQuery = "select id from cms_hlt_gdr.u_confversions where name='%s'" % (HLT_Key,)
    cursor.execute(configIDQuery)
    ConfigId, = cursor.fetchone()

    SequencePathQuery ="""
    SELECT prescale_sequence , triggername 
    FROM ( SELECT J.ID, J.NAME, LAG(J.ORD,1,0) OVER (order by J.ID) PRESCALE_SEQUENCE, J.VALUE TRIGGERNAME, 
    trim('{' from trim('}' from LEAD(J.VALUE,1,0) OVER (order by J.ID))) as PRESCALE_INDEX 
    FROM CMS_HLT_GDR.U_CONFVERSIONS A, 
    CMS_HLT_GDR.U_CONF2SRV S, 
    CMS_HLT_GDR.U_SERVICES B, 
    CMS_HLT_GDR.U_SRVTEMPLATES C, 
    CMS_HLT_GDR.U_SRVELEMENTS J 
    WHERE A.ID=%d AND A.ID=S.ID_CONFVER AND 
    S.ID_SERVICE=B.ID AND 
    C.ID=B.ID_TEMPLATE AND 
    C.NAME='PrescaleService' AND 
    J.ID_SERVICE=B.ID )Q WHERE NAME='pathName'
    ORDER BY prescale_sequence
    """ % (ConfigId,)

    cursor.execute(SequencePathQuery)
    HLTSequenceMap = {}
    for seq,name in cursor.fetchall():
        name = name.lstrip('"').rstrip('"')
        HLTSequenceMap[seq]=name

    SequencePrescaleQuery="""
    with pq as ( SELECT Q.* FROM ( SELECT J.ID, J.NAME, LAG(J.ORD,1,0) 
    OVER (order by J.ID) PRESCALE_SEQUENCE, J.VALUE TRIGGERNAME, 
    trim('{' from trim('}' from LEAD(J.VALUE,1,0) 
    OVER (order by J.ID))) as PRESCALE_INDEX FROM CMS_HLT_GDR.U_CONFVERSIONS A, 
    CMS_HLT_GDR.U_CONF2SRV S, CMS_HLT_GDR.U_SERVICES B, CMS_HLT_GDR.U_SRVTEMPLATES C, CMS_HLT_GDR.U_SRVELEMENTS J 
    WHERE A.ID=%d AND A.ID=S.ID_CONFVER AND S.ID_SERVICE=B.ID AND C.ID=B.ID_TEMPLATE AND C.
    NAME='PrescaleService' AND J.ID_SERVICE=B.ID )Q 
    WHERE NAME='pathName' ) select prescale_sequence , MYINDEX , 
    regexp_substr (prescale_index, '[^,]+', 1, rn) mypsnum 
    from pq cross join (select rownum rn, mod(rownum -1, level) MYINDEX 
    from (select max (length (regexp_replace (prescale_index, '[^,]+'))) + 1 mx from pq ) connect by level <= mx ) 
    where regexp_substr (prescale_index, '[^,]+', 1, rn) is not null order by prescale_sequence, myindex
    """ % (ConfigId,)

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
        row.append(int(val))

    return HLTPrescaleTable

def GetL1AlgoPrescales(curs,RS_Key):
    L1PrescalesQuery= """select D.CONF from CMS_TRG_L1_CONF.L1_TRG_RS_KEYS B, CMS_TRG_L1_CONF.UGT_RS_KEYS C, CMS_TRG_L1_CONF.UGT_RS D where
    B.ID ='%s' and C.ID=B.UGT_RS_KEY and D.ID=C.ALGO_PRESCALE""" % (RS_Key)    
    curs.execute(L1PrescalesQuery)
    l1_ps_xml = curs.fetchall()[0][0].read()
    e = xml.etree.ElementTree.fromstring(l1_ps_xml)
    L1PrescaleTable = {}

    for child in e:
        for gchild in child:
            for ggchild in gchild:
                for row in ggchild:
                    if row.tag == 'row':
                        line = row.text.replace('\n','').replace(' ','').split(',')
                        line = [ int(x) for x in line ]
                        bit = line[0]
                        prescales = line[1:]
                        L1PrescaleTable[bit] = prescales
                        

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
