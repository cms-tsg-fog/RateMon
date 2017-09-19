import cx_Oracle
import sys
import os

def GetLatestRunNumberList(minRunNumber):
    cmd='cat ~centraltspro/secure/cms_trg_r.txt'
    line=os.popen(cmd).readlines()
    magic = line[0].rstrip("\n\r")
    connect= 'cms_trg_r/' + magic + '@cms_omds_lb'
    # connect to the DB
    orcl = cx_Oracle.connect(connect)
    curs = orcl.cursor()
    RunNoQuery="""
    SELECT A.RUNNUMBER FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_WBM.RUNSUMMARY B WHERE A.RUNNUMBER=B.RUNNUMBER AND B.TRIGGERS>0 AND B.RUNNUMBER>=%d
    """ % minRunNumber
    curs.execute(RunNoQuery)
    
    runs=[]
    for run, in curs.fetchall():
        TrigModeQuery = """
        SELECT TRIGGERMODE FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER = %d
        """ % run
        curs.execute(TrigModeQuery)
        trigm, = curs.fetchone()
        isCol=0
        try:
            if trigm.find('l1_hlt_collisions')!=-1:
                runs.append(run)
        except:
            continue
    return runs

def usage():
    print sys.argv[0]+" MinRunNumber"
    
if __name__=='__main__':
    if len(sys.argv)<2:
        usage()
        sys.exit(0)
    try:
        for run in GetLatestRunNumber(int(sys.argv[1])):
            print run
    except:
        print "Invalid Run Number: "+str(sys.argv[1])
        usage()
