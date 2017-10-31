# Imports
import sys
import cx_Oracle
import socket
# For the parsing
import re

import time

# Key version stripper
def stripVersion(name):
    if re.match('.*_v[0-9]+',name): name = name[:name.rfind('_')]
    return name

class DBQueryTool:
    def __init__(self) :
        # Connect to the Database
        hostname = socket.gethostname()
        if hostname.find('lxplus') > -1: self.dsn_ = 'cms_omds_adg' #offline
        else: self.dsn_ = 'cms_omds_lb' #online

        orcl = cx_Oracle.connect(user='cms_hlt_r',password='***REMOVED***',dsn=self.dsn_)
        orcl = cx_Oracle.connect(user='cms_trg_r',password='***REMOVED***',dsn=self.dsn_)
        # Create a DB cursor
        self.curs = orcl.cursor()

    def getLumiInfo(self,runNumber,minLS=-1,maxLS=9999999):
        print "Getting Mini Lumi Info..."
        query = """
                SELECT
                    B.INSTLUMI,
                    B.LUMISECTION,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT*B.EBP_READY*
                        B.EBM_READY*B.EEP_READY*B.EEM_READY*
                        B.HBHEA_READY*B.HBHEB_READY*B.HBHEC_READY*
                        B.HF_READY*B.HO_READY*B.RPC_READY*
                        B.DT0_READY*B.DTP_READY*B.DTM_READY*
                        B.CSCP_READY*B.CSCM_READY*B.TOB_READY*
                        B.TIBTID_READY*B.TECP_READY*B.TECM_READY*
                        B.BPIX_READY*B.FPIX_READY*B.ESP_READY*B.ESM_READY,
                    C.PRESCALE_INDEX
                FROM
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B,
                    CMS_UGT_MON.VIEW_LUMI_SECTIONS C
                WHERE
                    B.RUNNUMBER = %s AND
                    C.RUN_NUMBER(+) = B.RUNNUMBER AND
                    C.LUMI_SECTION(+) = B.LUMISECTION AND
                    B.LUMISECTION >= %s AND C.LUMI_SECTION >= %s AND
                    B.LUMISECTION <= %s AND C.LUMI_SECTION <= %s
                ORDER BY
                    LUMISECTION
                """ % (runNumber,minLS,minLS,maxLS,maxLS)
        self.curs.execute(query) # Execute the query
        _list = []
        for item in self.curs.fetchall():
            ilum = item[0]
            LS = item[1]
            phys = item[2]
            cms_ready = item[3]
            psi = item[4]
            _list.append([LS,ilum,psi,phys,cms_ready])
        return _list

    def getFullLumiInfo(self,runNumber,minLS=-1,maxLS=9999999,lumi_source=0):
        print "Getting Full Lumi Info..."
        lumi_nibble = 16
        query = """
                SELECT
                    B.INSTLUMI,
                    A.PLTZERO_INSTLUMI,
                    A.HF_INSTLUMI,
                    B.LUMISECTION,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT,
                    B.PHYSICS_FLAG*B.BEAM1_PRESENT*B.EBP_READY*
                        B.EBM_READY*B.EEP_READY*B.EEM_READY*
                        B.HBHEA_READY*B.HBHEB_READY*B.HBHEC_READY*
                        B.HF_READY*B.HO_READY*B.RPC_READY*
                        B.DT0_READY*B.DTP_READY*B.DTM_READY*
                        B.CSCP_READY*B.CSCM_READY*B.TOB_READY*
                        B.TIBTID_READY*B.TECP_READY*B.TECM_READY*
                        B.BPIX_READY*B.FPIX_READY*B.ESP_READY*B.ESM_READY,
                    C.PRESCALE_INDEX
                FROM
                    CMS_BEAM_COND.CMS_BRIL_LUMINOSITY A,
                    CMS_RUNTIME_LOGGER.LUMI_SECTIONS B,
                    CMS_UGT_MON.VIEW_LUMI_SECTIONS C
                WHERE
                    A.RUN = %s AND
                    A.LUMINIBBLE = %s AND
                    A.RUN = B.RUNNUMBER AND
                    A.LUMISECTION = B.LUMISECTION AND
                    C.RUN_NUMBER(+) = B.RUNNUMBER AND
                    C.LUMI_SECTION(+) = B.LUMISECTION AND
                    B.LUMISECTION >= %s AND C.LUMI_SECTION >= %s AND
                    B.LUMISECTION <= %s AND C.LUMI_SECTION <= %s
                ORDER BY
                    LUMISECTION
                """ % (runNumber,lumi_nibble,minLS,minLS,maxLS,maxLS)
        self.curs.execute(query) # Execute the query
        _list = []
        for item in self.curs.fetchall():
            ilum = item[lumi_source]
            if ilum is None:
                if item[1]:
                    ilum = item[1]
                elif item[2]:
                    ilum = item[2]
                else:
                    ilum = None
            LS = item[3]
            phys = item[4]
            cms_ready = item[5]
            psi = item[6]
            _list.append([LS,ilum,psi,phys,cms_ready])
        return _list

    # Returns a tuple: (L1_HLT_Key,HLT_Key,GTRS_Key,TSC_Key,GT_Key)
    def getRunInfo(self,runNumber):
        print "Getting run info..."
        query =  """
                SELECT
                    B.ID,
                    B.HLT_KEY,
                    B.L1_TRG_RS_KEY,
                    B.L1_TRG_CONF_KEY,
                    C.UGT_KEY
                FROM
                    CMS_WBM.RUNSUMMARY A,
                    CMS_L1_HLT.L1_HLT_CONF B,
                    CMS_TRG_L1_CONF.L1_TRG_CONF_KEYS C
                WHERE
                    B.ID = A.TRIGGERMODE AND
                    A.RUNNUMBER = %d AND
                    C.ID = B.L1_TRG_CONF_KEY
                """ % (runNumber)
        try:
            self.curs.execute(query)
            run_keys = self.curs.fetchone()
            return run_keys
        except:
            print "Unable to get L1 and HLT keys for this run"
            return None

    def getPrescaleColumns(self,runNumber):
        print "Getting PS columns..."
        query =  """
                SELECT
                    LUMI_SECTION,
                    PRESCALE_INDEX
                FROM
                    CMS_UGT_MON.VIEW_LUMI_SECTIONS
                WHERE
                    RUN_NUMBER = %s
                """ % (runNumber)

        try:
            self.curs.execute(query)
            PSColumnByLS = {} 
            for lumi_section, prescale_column in self.curs.fetchall():
                PSColumnByLS[lumi_section] = prescale_column
            return PSColumnByLS
        except:
            print "Trouble getting PS column by LS"
            return None

    def getL1Prescales(self,runNumber):
        print "Getting L1 Prescales..."
        query =  """
                SELECT
                    A.ALGO_INDEX,
                    A.ALGO_NAME,
                    B.PRESCALE,
                    B.PRESCALE_INDEX
                FROM
                    CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING A,
                    CMS_UGT_MON.VIEW_UGT_RUN_PRESCALE B
                WHERE
                    A.ALGO_INDEX = B.ALGO_INDEX AND
                    A.RUN_NUMBER = B.RUN_NUMBER AND
                    A.RUN_NUMBER = %s
                ORDER BY
                    A.ALGO_INDEX
                """ % (runNumber)

        try:
            self.curs.execute(query)
        except:
            print "Get L1 Prescales query failed"
            return None

        ps_table = self.curs.fetchall()
        L1Prescales = {}

        if len(ps_table) < 1:
            print "Cannot get L1 Prescales"
            return None

        for obj in ps_table:
            algo_index = obj[0]
            algo_name = obj[1]
            algo_ps = obj[2]
            ps_index = obj[3]
            if not L1Prescales.has_key(algo_index):
                L1Prescales[algo_index] = {}
            L1Prescales[algo_index][ps_index] = algo_ps

        return L1Prescales

    def getL1NameIndexAssoc(self,runNumber):
        print "Getting Index Assoc..."
        query = """
                SELECT
                    ALGO_INDEX,
                    ALGO_NAME,
                    ALGO_MASK
                FROM
                    CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING
                WHERE
                    RUN_NUMBER=%s
                """ % (runNumber)
        try:
            self.curs.execute(query)
        except:
            print "Get L1 Name Index failed"
            return None

        L1IndexNameMap = {}
        L1NameIndexMap = {}
        L1Mask = {}

        for bit,name,mask in self.curs.fetchall():
            name = stripVersion(name)
            name = name.replace("\"","")
            L1IndexNameMap[name] = bit
            L1NameIndexMap[bit]=name
            L1Mask[bit] = mask

        return L1IndexNameMap, L1NameIndexMap, L1Mask

    def getSingleL1Rate(self,runNumber,algo_bit,scaler_type=0):
        #print "Getting Single L1 Rate... %d \r" % algo_bit
        sys.stdout.write("Getting Single L1 Rate... %d \r" % (algo_bit))
        sys.stdout.flush()
        run_str = "0%d" % runNumber
        query = """
                SELECT
                    LUMI_SECTIONS_ID,
                    ALGO_RATE
                FROM
                    CMS_UGT_MON.VIEW_ALGO_SCALERS
                WHERE
                    ALGO_INDEX = %d AND
                    SCALER_TYPE = %d AND
                    LUMI_SECTIONS_ID LIKE '%s%%'
                """ % (algo_bit,scaler_type,run_str)
        
        self.curs.execute(query)

        trigger_rates = {}
        for ls,rate in self.curs.fetchall():
            ls = int(ls.split('_')[1].lstrip('0'))
            trigger_rates[ls] = rate

        return trigger_rates

    def getAllL1Rates(self,runNumber,scaler_type=0):
        print "Getting L1 Rates..."
        run_str = "0%d" % runNumber
        query = """
                SELECT
                    LUMI_SECTIONS_ID,
                    ALGO_RATE,
                    ALGO_INDEX
                FROM
                    CMS_UGT_MON.VIEW_ALGO_SCALERS
                WHERE
                    SCALER_TYPE = %d AND
                    LUMI_SECTIONS_ID LIKE '%s%%'
                """ % (scaler_type,run_str)
        self.curs.execute(query)

        all_trigger_rates = {}
        for ls,rate,algo_bit in self.curs.fetchall():
            ls = int(ls.split('_')[1].lstrip('0'))

            if not all_trigger_rates.has_key(algo_bit):
                all_trigger_rates[algo_bit] = {}

            all_trigger_rates[algo_bit][ls] = rate

        return all_trigger_rates

    def getHLTNameMap(self,runNumber):
        print "Getting HLT Name Map..."
        query = """
                SELECT DISTINCT
                    C.PATHID,
                    B.NAME
                FROM
                    CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A,
                    CMS_HLT_GDR.U_PATHS B,
                    CMS_HLT_GDR.U_PATHIDS C
                WHERE
                    A.RUNNUMBER = %s AND
                    A.PATHID = C.PATHID AND
                    B.ID = C.ID_PATH
                """ % (runNumber)

        self.curs.execute(query)
        
        name_map = {}
        for path_id,path_name in self.curs.fetchall():
            name = stripVersion(path_name)
            name_map[name] = path_id
        return name_map

    def getSingleHLTRate(self,runNumber,path_id):
        #print "Getting Single HLT Rate... %s \r" % (path_id)
        sys.stdout.write("Getting Single HLT Rate... %s \r" % (path_id))
        sys.stdout.flush()
        query = """
                SELECT
                    A.LSNUMBER,
                    SUM(A.L1PASS),
                    SUM(A.PSPASS),
                    SUM(A.PACCEPT),
                    SUM(A.PEXCEPT)
                FROM
                    CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A
                WHERE
                    A.RUNNUMBER = %s AND
                    A.PATHID = %s
                GROUP BY
                    A.LSNUMBER, A.PATHID
                """ % (runNumber,path_id)
        try: 
            self.curs.execute(query)
        except:
            print "Getting rates for %s failed. Exiting." % name
            return None

        trigger_rates = {}
        for LS, L1Pass, PSPass, HLTPass, HTLExcept in self.curs.fetchall():
            rate = HLTPass/23.31041

            trigger_rates[LS] = rate

        return trigger_rates

    def getAllHLTRates(self,runNumber):
        print "Getting All HLT Rates..."
        query = """
                SELECT
                    A.LSNUMBER,
                    SUM(A.L1PASS),
                    SUM(A.PSPASS),
                    SUM(A.PACCEPT),
                    SUM(A.PEXCEPT),
                    (
                        SELECT
                            M.NAME
                        FROM
                            CMS_HLT_GDR.U_PATHS M,
                            CMS_HLT_GDR.U_PATHIDS L
                        WHERE
                            L.PATHID=A.PATHID AND
                            M.ID=L.ID_PATH
                    ) PATHNAME
                FROM
                    CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A
                WHERE
                    RUNNUMBER = %s
                GROUP BY 
                    A.LSNUMBER, A.PATHID
                """ % (runNumber)
        
        try:
            self.curs.execute(query)
        except:
            print "Getting rates failed. Exiting."
            return None

        all_trigger_rates = {}
        for LS, L1Pass, PSPass, HLTPass, HLTExcept, triggerName in self.curs.fetchall():
            name = stripVersion(triggerName)
            rate = HLTPass/23.31041

            if not all_trigger_rates.has_key(name):
                all_trigger_rates[name] = {}

            all_trigger_rates[name][LS] = rate

        return all_trigger_rates

    def test_query(self):
        #query="""SELECT MAX(A.RUNNUMBER), MAX(B.LIVELUMISECTION) FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B WHERE B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0 """
        #query="""SELECT LAST(B.LUMISECTION) FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B WHERE B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0 """
        #query="""SELECT column_name FROM all_tab_cols WHERE table_name = 'LUMI_SECTIONS' AND owner = 'CMS_RUNTIME_LOGGER'"""

        runNumber1 = 305516  # 205.3 / 180.5
        runNumber2 = 305586  # 220.9 / 186.5
        runNumber3 = 305589  # 171.2 / 163.2
        runNumber4 = 305518  # 244.2 / 234.9
        runNumber5 = 305590  # 160.4 / 156.1

        runNumber = runNumber5

        t_run_info = time.time()
        run_keys = self.getRunInfo(runNumber)
        t_run_info = time.time() - t_run_info

        t_lumi_info = time.time()
        lumi_info = self.getLumiInfo(runNumber)
        t_lumi_info = time.time() - t_lumi_info

        t_full_lumi = time.time()
        full_lumi_info = self.getFullLumiInfo(runNumber)
        t_full_lumi = time.time() - t_full_lumi

        t_ps_columns = time.time()
        PSColumnByLS = self.getPrescaleColumns(runNumber)
        t_ps_columns = time.time() - t_ps_columns

        t_l1_prescales = time.time()
        L1Prescales = self.getL1Prescales(runNumber)
        t_l1_prescales = time.time() - t_l1_prescales

        t_index_assoc = time.time()
        L1IndexNameMap,L1NameIndexMap,L1Mask = self.getL1NameIndexAssoc(runNumber)
        t_index_assoc = time.time () - t_index_assoc

        t_single_l1 = time.time()
        l1_rates = {}
        l1_iterations = 100
        #l1_iterations = len(L1IndexNameMap.keys())
        counter = 0
        for algo_bit,algo_name in L1NameIndexMap.iteritems():
            if counter > l1_iterations:
                break
            l1_rates[algo_name] = self.getSingleL1Rate(runNumber,algo_bit,0)
            counter += 1
        print ""
        t_single_l1 = time.time() - t_single_l1

        t_l1_rates = time.time()
        L1Rates = {}
        L1Rates = self.getAllL1Rates(runNumber,0)
        t_l1_rates = time.time() - t_l1_rates

        t_hlt_map = time.time()
        hlt_name_map = self.getHLTNameMap(runNumber)
        t_hlt_map = time.time() - t_hlt_map

        t_single_hlt = time.time()
        hlt_rates = {}
        hlt_iterations = 100
        #hlt_iterations = len(hlt_name_map.keys())
        counter = 0
        for hlt_name,path_id in hlt_name_map.iteritems():
            if counter > hlt_iterations:
                break
            hlt_rates[hlt_name] = self.getSingleHLTRate(runNumber,path_id)
            counter += 1
        print ""
        t_single_hlt = time.time() - t_single_hlt

        t_hlt_rates = time.time()
        HLTRates = {}
        HLTRates = self.getAllHLTRates(runNumber)
        t_hlt_rates = time.time() - t_hlt_rates

        l1_counts  = max(len(L1Rates.keys()),1)
        hlt_counts = max(len(HLTRates.keys()),1)

        l1_iterations  = max(l1_iterations,1)
        hlt_iterations = max(hlt_iterations,1)

        print "L1 Triggers:  %d (%d)" % (l1_iterations,len(L1Rates.keys()))
        print "HLT Triggers: %d (%d)" % (hlt_iterations,len(HLTRates.keys()))

        print "Timer Info:"
        print "\tRun Info:     %.3f" % (t_run_info)
        print "\tMini Lumi:    %.3f" % (t_lumi_info)
        print "\tFull Lumi:    %.3f" % (t_full_lumi)
        print "\tPS Columns:   %.3f" % (t_ps_columns)
        print "\tL1 Prescales: %.3f" % (t_l1_prescales)
        print "\tIndex Assoc:  %.3f" % (t_index_assoc)
        print "\tSingle L1:    %.3f (%.2f)" % (t_single_l1/l1_iterations,t_single_l1)
        print "\tL1 Rates:     %.3f (%.2f)" % (t_l1_rates/l1_counts,t_l1_rates)
        print "\tHLT Name Map: %.3f" % (t_hlt_map)
        print "\tSingle HLT:   %.3f (%.2f)" % (t_single_hlt/hlt_iterations,t_single_hlt)
        print "\tHLT Rates:    %.3f (%.2f)" % (t_hlt_rates/hlt_counts,t_hlt_rates)

## ----------- End of class ------------ ##

if __name__ == "__main__":
    query_tool = DBQueryTool()
    query_tool.test_query()
