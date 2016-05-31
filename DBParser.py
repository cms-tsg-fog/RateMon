##################################
# DB.py
# Author: Nathaniel Carl Rupprecht Charlie Mueller Alberto Zucchetta
# Date: June 11, 2015
# Last Modified: July 16, 2015
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects 
##################################

# Imports
import cx_Oracle
import socket
# For the parsing
import re

# Key version stripper
def stripVersion(name):
    #if re.match('.*_v[0-9]+',name): name = name[:name.rfind('_')]
    name = str(name.split('_v[0-9]')[0])
    return name

# A class that interacts with the HLT's oracle database and fetches information that we need
class DBParser:

    def __init__(self) :
        # Connect to the Database
        hostname = socket.gethostname()
        if hostname.find('lxplus') > -1: self.dsn_ = 'cms_omds_adg' #offline
        else: self.dsn_ = 'cms_omds_lb' #online

        orcl = cx_Oracle.connect(user='cms_trg_r',password='***REMOVED***',dsn=self.dsn_)
        # Create a DB cursor
        self.curs = orcl.cursor()

        self.L1Prescales = {}
        self.HLTPrescales = {}
        self.HLTSequenceMap = {}
        self.GTRS_Key = ""
        self.HLT_Key = ""
        self.TSC_Key = ""
        self.ConfigId = ""
        self.GT_Key = ""
        self.nAlgoBits = 128

        self.HLTSeed = {}
        self.L1Mask = {}
        self.L1IndexNameMap = {}
        self.L1NameIndexMap = {}
        self.PSColumnByLS = {}
        
    # Returns: a cursor to the HLT database
    def getHLTCursor(self):
        # Gets a cursor to the HLT database
        orcl = cx_Oracle.connect(user='cms_hlt_r',password='***REMOVED***',dsn=self.dsn_)
        return orcl.cursor()

    # Returns: a cursor to the trigger database
    def getTrgCursor(self):
        orcl = cx_Oracle.connect(user='cms_trg_r',password='***REMOVED***',dsn=self.dsn_)
        return orcl.cursor()


    # Returns: True if we succeded, false if the run doesn't exist (probably)
    def getRunInfo(self, runNumber):
        ## This query gets the L1_HLT Key (A), the associated HLT Key (B) and the Config number for that key (C)
#         KeyQuery = """
#         SELECT A.TRIGGERMODE, B.HLT_KEY, B.GT_RS_KEY, B.TSC_KEY, D.GT_KEY FROM
#         CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF B, CMS_HLT_GDR.U_CONFVERSIONS C, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
#         B.ID = A.TRIGGERMODE AND C.NAME = B.HLT_KEY AND D.TS_Key = B.TSC_Key AND A.RUNNUMBER=%d
#         """ % (runNumber)

#         KeyQuery = """
#         SELECT A.TRIGGERMODE, B.HLT_KEY, B.L1_TRG_RS_KEY, B.L1_TRG_CONF_KEY, B.UGT_KEY FROM
#         CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.V_L1_HLT_CONF_EXTENDED B, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
#         B.ID = A.TRIGGERMODE AND A.RUNNUMBER=%d
#         """ % (runNumber)

        sqlquery="""SELECT LUMI_SECTION, PRESCALE_INDEX FROM CMS_UGT_MON.VIEW_LUMI_SECTIONS WHERE RUN_NUMBER=%s""" % (runNumber)
        try:
            self.curs.execute(sqlquery)
            self.PSColumnByLS = {} 
            for lumi_section, prescale_column in self.curs.fetchall(): self.PSColumnByLS[lumi_section] = prescale_column
        except:
            print "Trouble getting PS column by LS"

        KeyQuery = """
        SELECT B.ID, B.HLT_KEY, B.L1_TRG_RS_KEY, B.L1_TRG_CONF_KEY, C.UGT_KEY FROM
        CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF_UPGRADE B, CMS_TRG_L1_CONF.L1_TRG_CONF_KEYS C WHERE
        B.ID = A.TRIGGERMODE AND A.RUNNUMBER=%d AND C.ID = B.L1_TRG_CONF_KEY
        """ % (runNumber)
        
        try:
            self.curs.execute(KeyQuery)
            self.L1_HLT_Key, self.HLT_Key, self.GTRS_Key, self.TSC_Key, self.GT_Key = self.curs.fetchone()
            return True
        except:
            print "Unable to get L1 and HLT keys for this run"
            return False
        

    # Use: Get the instant luminosity for each lumisection from the database
    # Parameters:
    # -- runNumber: the number of the run that we want data for
    # Returns: A list of of information for each LS: ( { LS, instLumi, physics } )
    def getLumiInfo(self, runNumber, minLS=-1, maxLS=9999999):

        # Define the SQL query that we will send to the database. We want to fetch Lumisection and instantaneous luminosity
        sqlquery="""SELECT LUMISECTION,INSTLUMI, PRESCALE_INDEX,
        PHYSICS_FLAG*BEAM1_PRESENT, 
        PHYSICS_FLAG*BEAM1_PRESENT*EBP_READY*EBM_READY*EEP_READY*EEM_READY*HBHEA_READY*HBHEB_READY*HBHEC_READY*HF_READY*HO_READY*RPC_READY*DT0_READY*DTP_READY*DTM_READY*
        CSCP_READY*CSCM_READY*TOB_READY*TIBTID_READY*TECP_READY*TECM_READY*BPIX_READY*FPIX_READY*ESP_READY*ESM_READY 
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_UGT_MON.VIEW_LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
        AND B.RUN_NUMBER(+)=A.RUNNUMBER AND B.LUMI_SECTION(+)=A.LUMISECTION AND A.LUMISECTION>=%s AND B.LUMI_SECTION>=%s
        AND A.LUMISECTION<=%s AND B.LUMI_SECTION<=%s
        """ % (runNumber, minLS, minLS, maxLS, maxLS)

        try:
            self.curs.execute(sqlquery) # Execute the query
        except:
            print "Getting LumiInfo failed. Exiting."
            exit(2) # Exit with error
        return self.curs.fetchall() # Return the results

    # Use: Get the prescaled rate as a function 
    # Parameters: runNumber: the number of the run that we want data for
    # Returns: A dictionary [ triggerName ] [ LS ] <prescaled rate> 
    def getPSRates(self, runNumber, minLS=-1, maxLS=9999999):
        # Note: we find the raw rate by dividing CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS.Accept by 23.31041

        sqlquery = "SELECT A.LSNUMBER, SUM(A.PACCEPT), (SELECT M.NAME FROM CMS_HLT_GDR.U_PATHS M,CMS_HLT_GDR.U_PATHIDS L \
        WHERE L.PATHID=A.PATHID AND M.ID=L.ID_PATH) PATHNAME FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A \
        WHERE RUNNUMBER=%s AND A.LSNUMBER>=%s AND A.LSNUMBER<=%s GROUP BY A.LSNUMBER,A.PATHID" % (runNumber, minLS, maxLS)

        try:
            self.curs.execute(sqlquery)
        except:
            print "Getting rates failed. Exiting."
            exit(2) # Exit with error
        TriggerRates = {}

        for LS, HLTPass, triggerName in self.curs.fetchall():
            
            rate = HLTPass/23.31041 # A lumisection is 23.31041 seconds
            name = stripVersion(triggerName)

            if not TriggerRates.has_key(name):
                # Initialize the value of TriggerRates[name] to be a dictionary, which we will fill with [ LS, rate ] data
                TriggerRates[name] = {}
                TriggerRates[name][LS] = rate

            else:
                TriggerRates[name][LS] = rate

        return TriggerRates

    # Note: This function is based on a function from DatabaseParser.py
    # Use: Get the raw rate and prescale factor
    # Parameters:
    # -- runNumber: The number of the run that we are examining
    # Returns: A dictionary [triggerName][LS] { raw rate, prescale } 
    def getRawRates(self, runNumber, minLS=-1, maxLS=9999999):
        # First we need the HLT and L1 prescale rates and the HLT seed info
        if not self.getRunInfo(runNumber):
            print "Failed to get run info "
            return {} # The run probably doesn't exist

        # Get L1 info
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)
        # Get HLT info
        self.getHLTSeeds(runNumber)
        self.getHLTPrescales(runNumber)

        # Get the prescale index as a function of LS
        for LS, psi in self.curs.fetchall():
            self.PSColumnByLS[LS] = psi

        ## A more complex version of the getRates query
        sqlquery = "SELECT A.LSNUMBER, SUM(A.L1PASS),SUM(A.PSPASS),SUM(A.PACCEPT),SUM(A.PEXCEPT), (SELECT M.NAME FROM CMS_HLT_GDR.U_PATHS M,CMS_HLT_GDR.U_PATHIDS L \
        WHERE L.PATHID=A.PATHID AND M.ID=L.ID_PATH) PATHNAME FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A \
        WHERE RUNNUMBER=%s AND A.LSNUMBER>=%s AND A.LSNUMBER<=%s GROUP BY A.LSNUMBER,A.PATHID" % (runNumber, minLS, maxLS)
        
        try: self.curs.execute(sqlquery)
        except:
            print "Getting rates failed. Exiting."
            exit(2) # Exit with error

        TriggerRates = {} # Initialize TriggerRates
        
        for LS, L1Pass, PSPass, HLTPass, HLTExcept, triggerName in self.curs.fetchall():
            name = stripVersion(triggerName)

            rate = HLTPass/23.31041 # HLTPass is events in this LS, so divide by 23.31041 s to get rate
            hltps = 0 # HLT Prescale

            if not TriggerRates.has_key(name):
                TriggerRates[name] = {} # Initialize dictionary
            # TODO: We can probably come up with a better solution then a try, except here
            try: psi = self.PSColumnByLS[LS] # Get the prescale index
            except: psi = 0
            if psi is None: psi=0
            
            try:
                hltps = self.HLTPrescales[name][psi]
            except:
                hltps = 1.
            hltps = float(hltps)
                    
            try:
                if self.L1IndexNameMap.has_key( self.HLTSeed[name] ):
                    l1ps = self.L1Prescales[self.L1IndexNameMap[self.HLTSeed[name]]][psi]
                else:
                    AvL1Prescales = self.CalculateAvL1Prescales([LS])
                    l1ps = self.UnwindORSeed(self.HLTSeed[name] ,AvL1Prescales)
            except:
                l1ps = 1

            ps = l1ps*hltps
            TriggerRates[name][LS]= [ps*rate, ps]

        return TriggerRates

    # Use: Gets data related to L1 trigger rates
    # Returns: The L1 raw rates: [ trigger ] [ LS ] { raw rate, ps }
    def getL1RawRates(self, runNumber, minLS=-1, maxLS=9999999):
        # Get information that we will need to use
        self.getRunInfo(runNumber)
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)
        
        #pre-DT rates query (new uGT)
        #(0, 'ALGORITHM_RATE_AFTER_PRESCALE'),
        #(1, 'ALGORITHM_RATE_BEFORE_PRESCALE'),
        #(2, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE'),
        #(3, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_BY_HLT'),
        #(5, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_CALIBRATION'),
        #(4, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_PHYSICS'),
        #(6, 'POST_DEADTIME_ALGORITHM_RATE_AFTER_PRESCALE_RANDOM')
        run_str = '0%d' % (runNumber)
        query_before_ps = """SELECT LUMI_SECTIONS_ID, ALGO_RATE, ALGO_INDEX FROM CMS_UGT_MON.VIEW_ALGO_SCALERS WHERE
        SCALER_TYPE=0 AND LUMI_SECTIONS_ID LIKE '%s""" %(run_str) +"""%' """

        self.curs.execute(query_before_ps)
        l1_rates_preDT_ps = self.curs.fetchall()

        L1Triggers = {}
        for tuple in l1_rates_preDT_ps:
            ls = int(tuple[0].split('_')[1].lstrip('0'))
            ps_rate = tuple[1]
            bit = tuple[2]
            algo_name = self.L1NameIndexMap[bit]

            if self.L1Mask[bit] == 0: ps_rate=0. 

            if not L1Triggers.has_key(algo_name): L1Triggers[algo_name] = {}
            prescale_column = self.PSColumnByLS[ls]
            try:
                unprescaled_rate = ps_rate*self.L1Prescales[bit][prescale_column]
            except:
                print "prescales bit or column not avaiable "
                continue
            L1Triggers[algo_name][ls] = [ unprescaled_rate , self.L1Prescales[bit][prescale_column] ]

        return L1Triggers        # [ trigger ] [ LS ] { raw rate, ps }

    
    # Use: Gets the raw rate of a trigger during a run and the average prescale value of that trigger during the run
    # Returns: A dictionary: [ trigger name ] { ave ps, [ LS ] [ raw rate ] }
    def getRates_AvePS(self, runNumber):
        # Get the rates in the form: [triggerName][LS] { raw rate, prescale }
        Rates = self.getPSRates(runNumber)

        # Create the dictionary to be returned
        TriggerRates = {}

        for triggerName in Rates:
            TriggerRates[triggerName] = [ 0, {} ]
            counter = 0
            totalPS = 0
            for LS in Rates[triggerName]:
                totalPS += Rates[triggerName][LS][1]
                TriggerRates[triggerName][1][LS] = Rates[triggerName][LS][0] # Get the raw rate
                counter += 1
            TriggerRates[triggerName][0] = totalPS/counter # Set the ave ps

        return TriggerRates

    # Note: This function is from DatabaseParser.py (with moderate modification)
    # Use: Sets the L1 trigger prescales for this class
    # Returns: (void)
    def getL1Prescales(self, runNumber):
        sqlquery = """SELECT A.ALGO_INDEX, A.ALGO_NAME, B.PRESCALE, B.PRESCALE_INDEX FROM CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING A, CMS_UGT_MON.VIEW_UGT_RUN_PRESCALE B WHERE
        A.ALGO_INDEX=B.ALGO_INDEX AND A.RUN_NUMBER = B.RUN_NUMBER AND A.RUN_NUMBER=%s ORDER BY A.ALGO_INDEX""" % (runNumber)

        try:
            self.curs.execute(sqlquery)
        except:
            print "Get L1 Prescales query failed"
            return 

        ps_table = self.curs.fetchall()
        self.L1Prescales = {}

        if len(ps_table) < 1:
            print "Cannot get L1 Prescales"
            return

        for object in ps_table:
            algo_index = object[0]
            algo_name = object[1]
            algo_ps = object[2]
            ps_index = object[3]
            if not self.L1Prescales.has_key(algo_index): self.L1Prescales[algo_index] = {}
            self.L1Prescales[algo_index][ps_index] = algo_ps


    # Note: This function is from DatabaseParser.py (with slight modifications)
    # Use: Gets the average L1 prescales
    # Returns: A dictionary: [ Algo bit number ] <Ave L1 Prescale>
    def getAvL1Prescales(self, runNumber):
        AvgL1Prescales = [0]*self.nAlgoBits
        for index in LSRange:
            psi = self.PSColumnByLS[index]
            if not psi: psi = 0
            for algo in range(self.nAlgoBits):
                # AvgL1Prescales[algo]+=self.L1PrescaleTable[algo][psi]
                AvgL1Prescales[algo]+=self.L1Prescales[algo][psi]
        for i in range(len(AvgL1Prescales)):
            try:
                AvgL1Prescales[i] = AvgL1Prescales[i]/len(LSRange)
            except:
                AvgL1Prescales[i] = AvgL1Prescales[i]
        return AvgL1Prescales
    
    # Note: This function is from DatabaseParser.py
    # Use: Frankly, I'm not sure. I don't think its ever been called. Read the (origional) info string
    # Returns: The minimum prescale value
    def UnwindORSeed(self,expression,L1Prescales):
        """
        Figures out the effective prescale for the OR of several seeds
        we take this to be the *LOWEST* prescale of the included seeds
        """
        if expression.find(" OR ") == -1:
            return -1  # Not an OR of seeds
        seedList = expression.split(" OR ")
        if len(seedList)==1:
            return -1 # Not an OR of seeds, really shouldn't get here...
        minPS = 99999999999
        for seed in seedList:
            if not self.L1IndexNameMap.has_key(seed): continue
            ps = L1Prescales[self.L1IndexNameMap[seed]]
            if ps: minPS = min(ps,minPS)
        if minPS==99999999999: return 0
        else: return minPS

    # Note: This function is from DatabaseParser.py (with slight modifications), double (##) comments are origionals
    # Use: Sets the L1 seed that each HLT trigger depends on
    # Returns: (void)
    def getHLTSeeds(self, runNumber):
        ### Check
        ## This is a rather delicate query, but it works!
        ## Essentially get a list of paths associated with the config, then find the module of type HLTLevel1GTSeed associated with the path
        ## Then find the parameter with field name L1SeedsLogicalExpression and look at the value
        ##
        ## NEED TO BE LOGGED IN AS CMS_HLT_R
        if self.HLT_Key == "": self.getRunInfo(runNumber)

        tmpcurs = self.getHLTCursor()
        sqlquery ="""
        select s.name, d.value from cms_hlt_gdr.u_confversions h, cms_hlt_gdr.u_pathid2conf a, cms_hlt_gdr.u_pathid2pae n, \
        cms_hlt_gdr.u_paelements b, cms_hlt_gdr.u_pae2moe c, cms_hlt_gdr.u_moelements d, cms_hlt_gdr.u_mod2templ e,cms_hlt_gdr.u_moduletemplates f,\
        cms_hlt_gdr.u_pathids p, cms_hlt_gdr.u_paths s where h.name='%s' and a.id_confver=h.id and  n.id_pathid=a.id_pathid and b.id=n.id_pae and\
        c.id_pae=b.id and d.id=c.id_moe and d.name='L1SeedsLogicalExpression' and e.id_pae=b.id and f.id=e.id_templ and f.name='HLTL1TSeed' and\
        p.id=n.id_pathid and s.id=p.id_path order by value""" % (self.HLT_Key,)
        
        tmpcurs.execute(sqlquery)
        for HLTPath,L1Seed in tmpcurs.fetchall():
            name = stripVersion(HLTPath) # Strip the version from the trigger name
            if not self.HLTSeed.has_key(name): ## this should protect us from L1_SingleMuOpen
                self.HLTSeed[HLTPath] = L1Seed.lstrip('"').rstrip('"') 

    # Note: This function is from DatabaseParser.py (with slight modification)
    # Use: Seems to return the algo index that corresponds to each trigger name
    # Returns: (void)
    def getL1NameIndexAssoc(self, runNumber):
        ## get the L1 algo names associated with each algo bit
        ### Check
#        if self.GT_Key == "":
#            self.getRunInfo(runNumber)


        #old GT query    
#         AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
#         WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
#         ORDER BY ALGO_INDEX""" % (self.GT_Key,)
        AlgoNameQuery = """SELECT ALGO_INDEX, ALGO_NAME, ALGO_MASK FROM CMS_UGT_MON.VIEW_UGT_RUN_ALGO_SETTING WHERE RUN_NUMBER=%s""" % (runNumber)  
        try:
            self.curs.execute(AlgoNameQuery)
        except:
            print "Get L1 Name Index failed"
            return

        for bit,name,mask in self.curs.fetchall():
            name = stripVersion(name)
            name = name.replace("\"","")
            self.L1IndexNameMap[name] = bit
            self.L1NameIndexMap[bit]=name
            self.L1Mask[bit] = mask

    # Note: This is a function from DatabaseParser.py (with slight modification)
    # Use: Gets the prescales for the various HLT triggers
    def getHLTPrescales(self, runNumber):
        ### Check
        if self.HLT_Key == "":
            self.getRunInfo(runNumber)
        
        tmp_curs = self.getHLTCursor()
        configIDQuery = "SELECT CONFIGID FROM CMS_HLT_GDR.U_CONFVERSIONS WHERE NAME='%s'" % (self.HLT_Key)
        tmp_curs.execute(configIDQuery)
        ConfigId, = tmp_curs.fetchone()

        SequencePathQuery ="""
        SELECT prescale_sequence , triggername FROM ( SELECT J.ID, J.NAME, LAG(J.ORD,1,0) OVER (order by J.ID) \
        PRESCALE_SEQUENCE, J.VALUE TRIGGERNAME, trim('{' from trim('}' from LEAD(J.VALUE,1,0) OVER (order by J.ID)))\
        as PRESCALE_INDEX FROM CMS_HLT_GDR.U_CONFVERSIONS A, CMS_HLT_GDR.U_CONF2SRV S, CMS_HLT_GDR.U_SERVICES B,\
        CMS_HLT_GDR.U_SRVTEMPLATES C, CMS_HLT_GDR.U_SRVELEMENTS J WHERE A.CONFIGID=%s AND A.ID=S.ID_CONFVER AND\
        S.ID_SERVICE=B.ID AND C.ID=B.ID_TEMPLATE AND C.NAME='PrescaleService' AND J.ID_SERVICE=B.ID )Q WHERE NAME='pathName'
        """ % (ConfigId,)
        
        tmp_curs.execute(SequencePathQuery)
        HLTSequenceMap = {}
        for seq,name in tmp_curs.fetchall():
            name = name.lstrip('"').rstrip('"')
            name = stripVersion(name)
            HLTSequenceMap[seq]=name
            
        SequencePrescaleQuery="""
        with pq as ( SELECT Q.* FROM ( SELECT J.ID, J.NAME, LAG(J.ORD,1,0) OVER (order by J.ID) PRESCALE_SEQUENCE, J.VALUE\
        TRIGGERNAME, trim('{' from trim('}' from LEAD(J.VALUE,1,0) OVER (order by J.ID))) as PRESCALE_INDEX FROM\
        CMS_HLT_GDR.U_CONFVERSIONS A, CMS_HLT_GDR.U_CONF2SRV S, CMS_HLT_GDR.U_SERVICES B, CMS_HLT_GDR.U_SRVTEMPLATES C,\
        CMS_HLT_GDR.U_SRVELEMENTS J WHERE A.CONFIGID=%s AND A.ID=S.ID_CONFVER AND S.ID_SERVICE=B.ID AND C.ID=B.ID_TEMPLATE\
        AND C.NAME='PrescaleService' AND J.ID_SERVICE=B.ID )Q WHERE NAME='pathName' ) select prescale_sequence , MYINDEX ,\
        regexp_substr (prescale_index, '[^,]+', 1, rn) mypsnum from pq cross join (select rownum rn, mod(rownum -1, level) MYINDEX\
        from (select max (length (regexp_replace (prescale_index, '[^,]+'))) + 1 mx from pq ) connect by level <= mx )\
        where regexp_substr (prescale_index, '[^,]+', 1, rn) is not null order by prescale_sequence, myindex
        """ % (ConfigId,)
        
        tmp_curs.execute(SequencePrescaleQuery)
        lastIndex=-1
        lastSeq=-1
        row = []

        for seq,index,val in tmp_curs.fetchall():
            if lastIndex != index-1:
                self.HLTPrescales[HLTSequenceMap[seq-1]] = row
                row=[]
            lastSeq=seq
            lastIndex=index
            row.append(val)



    # Note: This is a function from DatabaseParser.py (with slight modification)
    # Use: Gets the number of colliding bunches during a run
    def getNumberCollidingBunches(self, runNumber):
        # Get Fill number first
        sqlquery = "SELECT LHCFILL FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER=%s" % (runNumber)
        self.curs.execute(sqlquery)
        
        try: fill = self.curs.fetchone()[0]
        except: return [0,0]
        
        # Get the number of colliding bunches
        sqlquery = "SELECT NCOLLIDINGBUNCHES, NTARGETBUNCHES FROM CMS_RUNTIME_LOGGER.RUNTIME_SUMMARY WHERE LHCFILL=%s" % (fill)
        try:
            self.curs.execute(sqlquery)
            bunches = self.curs.fetchall()[0]
            bunches= [ int(bunches[0]), int(bunches[1]) ]
            return bunches
        except:
            #print "database error querying for num colliding bx" 
            return [0, 0]

    
    # Use: Gets the last LHC status
    # Returns: A dictionary: [ status ] <text_value>
    def getLHCStatus(self):
        import time 
        utime = int(time.time())
        sqlquery = "SELECT A.VALUE, CMS_LHCGMT_COND.GMTDB.VALUE_TEXT(A.GROUPINDEX,A.VALUE) TEXT_VALUE FROM CMS_LHCGMT_COND.LHC_GMT_EVENTS A, CMS_LHCGMT_COND.LHC_GMT_EVENT_DESCRIPTIONS B WHERE A.SOURCE=B.SOURCE(+) AND A.SOURCE=5130 AND A.SECONDS BETWEEN %s AND %s ORDER BY A.SECONDS DESC,A.NSECONDS DESC" % (str(utime-86400), str(utime))
        self.curs.execute(sqlquery)
        queryResult = self.curs.fetchall()
        if len(queryResult) == 0: return ['----','Not available']
        elif len(queryResult[0]) >1: return queryResult[0]
        else: return ['---','Not available']
        
    # Use: Gets the dead time as a function of lumisection
    # Returns: A dictionary: [ LS ] <Deadtime>
    def getDeadTime(self, runNumber):
        sqlquery="""SELECT SECTION_NUMBER, DEADTIME_BEAMACTIVE_TOTAL FROM CMS_TCDS_MONITORING.tcds_cpm_deadtimes_v WHERE RUN_NUMBER=%s""" % (runNumber)
        
        self.curs.execute(sqlquery)
        
        deadTime = {}
        for ls, dt in self.curs.fetchall():
            deadTime[ls] = dt
            
        return deadTime

    
    # Use: Gets the total L1 rate as a function of lumisection
    # Returns: A dictionary: [ LS ] <Deadtime>
    def getL1rate(self, runNumber):
        sqlquery="""SELECT SECTION_NUMBER, TRG_RATE_TOTAL FROM CMS_TCDS_MONITORING.tcds_cpm_rates_v WHERE RUN_NUMBER=%s""" % (runNumber)
        
        self.curs.execute(sqlquery)
        
        l1rate = {}
        for ls, rate in self.curs.fetchall():
            l1rate[ls] = rate
            
        return l1rate    


    # Use: Returns the number of the latest run to be stored in the DB
    def getLatestRunInfo(self):
        query="""SELECT MAX(A.RUNNUMBER)
        FROM CMS_RUNINFO.RUNNUMBERTBL A, CMS_RUNTIME_LOGGER.LUMI_SECTIONS B WHERE B.RUNNUMBER=A.RUNNUMBER AND B.LUMISECTION > 0
        """
        try:
            self.curs.execute(query)
            runNumber = self.curs.fetchone()
        except:
            print "Error: Unable to retrieve latest run number."
            return

        mode = self.getTriggerMode(runNumber)
        isCol=0
        isGood=1
        
        if mode is None:
            isGood=0
        elif mode[0].find('l1_hlt_collisions') != -1:
            isCol=1
                        
        Tier0xferQuery = "SELECT TIER0_TRANSFER TIER0 FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER = %d" % (runNumber)
        self.curs.execute(Tier0xferQuery)
        tier0=1
        try:
            tier0 = self.curs.fetchone()
        except:
            print "Error: Unable to get tier0 status."
            
        if isCol and not tier0:
            print "WARNING: tier0 transfer is off"
        elif not tier0:
            print "Please check if tier0 transfer is supposed to be off."
            
        return [runNumber[0], isCol, isGood, mode]


    def getWbmUrl(self,runNumber,pathName,LS):
        if pathName[0:4]=="HLT_":
            sqlquery = "SELECT A.PATHID, (SELECT M.NAME FROM CMS_HLT_GDR.U_PATHS M,CMS_HLT_GDR.U_PATHIDS L \
            WHERE L.PATHID=A.PATHID AND M.ID=L.ID_PATH) PATHNAME FROM CMS_RUNINFO.HLT_SUPERVISOR_TRIGGERPATHS A \
            WHERE RUNNUMBER=%s AND A.LSNUMBER=%s" % (runNumber, LS)

            try: self.curs.execute(sqlquery)
            except: return "-"

            for id,fullName in self.curs.fetchall():
                name = stripVersion(fullName)
                if name == pathName:
                    url = "https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/ChartHLTTriggerRates?fromLSNumber=&toLSNumber=&minRate=&maxRate=&drawCounts=0&drawLumisec=1&runID=%s&pathID=%s&TRIGGER_PATH=%s&LSLength=23.310409580838325" % (runNumber,id,fullName)
                    return url
                
        elif pathName[0:3]=="L1_":
            try:
                bitNum = self.L1IndexNameMap[pathName]
                url = "https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/ChartL1TriggerRates?fromTime=&toTime=&fromLSNumber=&toLSNumber=&minRate=&maxRate=&minCount=&maxCount=&preDeadRates=1&drawCounts=0&drawLumisec=1&runID=%s&bitID=%s&type=0&TRIGGER_NAME=%s&LSLength=23.310409580838325" % (runNumber,bitNum,pathName)
                return url
            except:
                return "-"
            
        return "-"
    
    # Use: Get the trigger mode for the specified run
    def getTriggerMode(self, runNumber):
        TrigModeQuery = "SELECT TRIGGERMODE FROM CMS_WBM.RUNSUMMARY WHERE RUNNUMBER = %d" % (runNumber)
        try:
            self.curs.execute(TrigModeQuery)
            mode = self.curs.fetchone()
        except:
            print "Error: Unable to retrieve trigger mode."
        return mode

    # Use: Retrieves the data from all streams
    # Returns: A dictionary [ stream name ] { LS, rate, size, bandwidth }
    def getStreamData(self, runNumber, minLS=-1, maxLS=9999999):
        cursor = self.getTrgCursor()
        StreamQuery = """select A.lumisection, A.stream, B.nevents/23.31041, B.filesize, B.filesize/23.31041
        from CMS_STOMGR.FILES_CREATED A, CMS_STOMGR.FILES_INJECTED B where A.filename = B.filename
        and A.runnumber=%s and A.lumisection>=%s and A.lumisection<=%s """ % (runNumber, minLS, maxLS)

        try:
            cursor.execute(StreamQuery)
            streamData = cursor.fetchall()
        except:
            print "Error: Unable to retrieve stream data."

        StreamData = {}
        for LS, stream, rate, size, bandwidth in streamData:
            if not StreamData.has_key(stream):
                StreamData[stream] = []
            StreamData[stream].append( [LS, rate, size, bandwidth] )

        return StreamData

    def getPrimaryDatasets(self, runNumber, minLS=-1, maxLS=9999999):
        cursor = self.getTrgCursor()
        PDQuery = """select distinct E.NAME, F.LSNUMBER, F.ACCEPT/23.31041 from CMS_HLT_GDR.U_CONFVERSIONS A,
        CMS_HLT_GDR.U_CONF2STRDST B, CMS_WBM.RUNSUMMARY C, CMS_HLT_GDR.U_DATASETIDS D,
        CMS_HLT_GDR.U_DATASETS E, CMS_RUNINFO.HLT_SUPERVISOR_DATASETS F WHERE D.ID=B.ID_DATASETID
        and E.ID=D.ID_DATASET and B.ID_CONFVER=A.ID and D.ID = F.DATASETID AND A.CONFIGID = C.HLTKEY
        and F.RUNNUMBER = C.RUNNUMBER and C.RUNNUMBER = %s and F.LSNUMBER >=%s and F.LSNUMBER <=%s
        ORDER BY E.NAME""" % (runNumber,minLS,maxLS)

        try:
            cursor.execute(PDQuery)
            pdData = cursor.fetchall()
        except:
            print "Error: Unable to retrieve PD data."

        PrimaryDatasets = {}
        for pd, LS, rate, in pdData:
            if not PrimaryDatasets.has_key(pd):
                PrimaryDatasets[pd] = []
            PrimaryDatasets[pd].append( [LS, rate] )

        return PrimaryDatasets

            
# -------------------- End of class DBParsing -------------------- #
