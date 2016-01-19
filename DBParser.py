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
    if re.match('.*_v[0-9]+',name):
        name = name[:name.rfind('_')]
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


    # Note: This function is from DatabaseParse.py (with slight modification)
    # Returns: True if we succeded, false if the run doesn't exist (probably)
    def getRunInfo(self, runNumber):
        ## This query gets the L1_HLT Key (A), the associated HLT Key (B) and the Config number for that key (C)
        KeyQuery = """
        SELECT A.TRIGGERMODE, B.HLT_KEY, B.GT_RS_KEY, B.TSC_KEY, D.GT_KEY FROM
        CMS_WBM.RUNSUMMARY A, CMS_L1_HLT.L1_HLT_CONF B, CMS_HLT_GDR.U_CONFVERSIONS C, CMS_TRG_L1_CONF.TRIGGERSUP_CONF D WHERE
        B.ID = A.TRIGGERMODE AND C.NAME = B.HLT_KEY AND D.TS_Key = B.TSC_Key AND A.RUNNUMBER=%d
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
        sqlquery="""SELECT LUMISECTION,INSTLUMI, PRESCALE_INDEX, PHYSICS_FLAG*BEAM1_PRESENT
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_GT_MON.LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
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
            return {} # The run probably doesn't exist

        # Get L1 info
        self.getL1Prescales(runNumber)
        self.getL1NameIndexAssoc(runNumber)
        # Get HLT info
        self.getHLTSeeds(runNumber)
        self.getHLTPrescales(runNumber)

        # Get column prescale info
        self.getPSColumnByLS(runNumber, minLS)

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
                if self.L1IndexNameMap.has_key(self.HLTSeed[name]):
                    l1ps = self.L1Prescales[self.L1IndexNameMap[self.HLTSeed[name]]][psi]
                else:
                    AvL1Prescales = self.CalculateAvL1Prescales([LS])
                    l1ps = self.UnwindORSeed(self.HLTSeed[name],AvL1Prescales)
            except: l1ps = 1

            ps = l1ps*hltps
            TriggerRates[name][LS]= [ps*rate, ps]

        return TriggerRates

    # Use: Gets data related to L1 trigger rates
    # Parameters:
    # -- runNumber: The number of the run to look at
    # -- minLS: The minimum lumisection to consider
    # Returns: The L1 raw rates: [ trigger ] [ LS ] { raw rate, ps }
    def getL1RawRates(self, runNumber, minLS=-1, maxLS=9999999):
        # Get information that we will need to use
        self.getRunInfo(runNumber)
        self.getPSColumnByLS(runNumber, minLS)
        self.getL1Prescales(runNumber)
        self.getL1Mask(runNumber)
        self.getL1NameIndexAssoc(runNumber)
        
        #pre-DT rates query
        query = """SELECT LUMI_SECTION, RATE_HZ, SCALER_INDEX 
        FROM CMS_GT_MON.V_SCALERS_FDL_ALGO WHERE RUN_NUMBER=%s AND LUMI_SECTION>=%s AND LUMI_SECTION <=%s""" % (runNumber, minLS, maxLS) 

        # Formulate Post-DT deadtime rates query
        # query = """SELECT LUMI_SECTION, COUNT/23.31041, BIT FROM (SELECT MOD(ROWNUM - 1, 128) BIT,
        # C.COLUMN_VALUE COUNT, A.RUNNUMBER RUN_NUMBER,
        # A.LSNUMBER LUMI_SECTION FROM CMS_RUNINFO.HLT_SUPERVISOR_L1_SCALARS A ,TABLE(A.DECISION_ARRAY_PHYSICS) C
        # WHERE A.RUNNUMBER=%s AND A.LSNUMBER>=%s AND A.LSNUMBER<=%s)""" % (runNumber, minLS, maxLS)

        self.curs.execute(query)
        L1RateAll=self.curs.fetchall()

        L1Triggers = {}
        rmap = {} # Maps bits to trigger names
        LSRange = []
        for name in self.L1IndexNameMap:
            rmap[self.L1IndexNameMap[name]] = name
        
        # Create L1 Rates: [ trigger ] [ LS ] <Rate>
        for LS, rate, bit in L1RateAll:
            # Check if the L1 bit is enabled
            if len(self.L1Mask) == 128 and self.L1Mask[bit] == 0: continue
            
            if not rmap.has_key(bit):
                #print "Cannot find L1 trigger with bit %s" % (bit)
                continue
            
            name = rmap[bit]
            if not LS in LSRange:
                LSRange.append(LS)
            if not L1Triggers.has_key(name):
                L1Triggers[name] = {}
            L1Triggers[name][LS] = rate
                
        if len(LSRange) == 0: return {}
        
        L1PSbits={}
        L1Rates = {}
        for bit in self.L1Prescales.iterkeys():
            if not rmap.has_key(bit):
                continue
            name = rmap[bit]
            if not L1Rates.has_key(name):
                L1Rates[name] = {}
            for LS in LSRange:
                try:
                    pscol = self.PSColumnByLS[LS]
                    ps = self.L1Prescales[bit][pscol]
                    unprescaled_rate = L1Triggers[name][LS]*ps
                    L1Rates[name][LS]= [ unprescaled_rate , ps ]
                except:
                    pass
                
        # [ trigger ] [ LS ] { raw rate, ps }
        return L1Rates
    
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

    # Use: Gets the ps columns for each ls
    # Returns: (void)
    def getPSColumnByLS(self, runNumber, minLS=-1):
        # Get column prescale info
        sqlquery= """SELECT LUMISECTION,PRESCALE_INDEX
        FROM CMS_RUNTIME_LOGGER.LUMI_SECTIONS A,CMS_GT_MON.LUMI_SECTIONS B WHERE A.RUNNUMBER=%s
        AND B.RUN_NUMBER(+)=A.RUNNUMBER AND B.LUMI_SECTION(+)=A.LUMISECTION AND A.LUMISECTION>=%s ORDER BY A.RUNNUMBER,A.LUMISECTION
        """ % (runNumber, minLS)
        self.curs.execute(sqlquery)
        # Reset self.PSColumnByLS 
        self.PSColumnByLS = {} 
        # Get the prescale index as a function of LS
        for LS, psi in self.curs.fetchall():
            self.PSColumnByLS[LS] = psi

    # Note: This function is from DatabaseParser.py (with moderate modification)
    # Use: Sets the L1 trigger prescales for this class
    # Returns: (void)
    def getL1Prescales(self, runNumber):
        if self.GTRS_Key == "":
            self.getRunInfo(runNumber)
        # Construct the query in a more concise way then trying to just write it all out
        sqlquery = "SELECT "
        for x in range(0, 128):
            sqlquery += "PRESCALE_FACTOR_ALGO_" + (3-len(str(x)))*"0" + str(x)
            if x != 127: sqlquery += ","
            else: sqlquery += " "
        sqlquery += "FROM CMS_GT.GT_FDL_PRESCALE_FACTORS_ALGO A, CMS_GT.GT_RUN_SETTINGS_PRESC_VIEW B WHERE A.ID=B.PRESCALE_FACTORS_ALGO_FK AND B.ID='"
        sqlquery += (self.GTRS_Key + "'")
        # Our query is now constructed
        try:
            self.curs.execute(sqlquery)
        except:
            print "Get L1 Prescales failed"
            return 

        ps_table = self.curs.fetchall()
        self.L1Prescales = {}

        if len(ps_table) < 1:
            print "Cannot get L1 Prescales"
            return
        
        for bit in range(0,128):
            self.L1Prescales[bit] = {}
            ps_column_index = 0
            for ps_col_array in ps_table:
                self.L1Prescales[bit][ps_column_index] = ps_col_array[bit]
                ps_column_index +=1

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
    
    def getL1Mask(self, runNumber):
        if self.GTRS_Key == "":
            self.getRunInfo(runNumber)
        sqlquery= """SELECT * FROM CMS_GT.GT_PARTITION_FINOR_ALGO WHERE ID IN (SELECT FINOR_ALGO_FK FROM CMS_GT.GT_RUN_SETTINGS WHERE ID='%s')""" % (self.GTRS_Key)
        try:
            self.curs.execute(sqlquery)
            mask = self.curs.fetchall()[0]
        except:
            print "Cannot determine which L1 bits are masked or not"
            return
        
        # Strip first element of the list, which is a string
        mask = mask[1:]
        # Always assign a list with len = 128
        if len(mask) == 128:
            self.L1Mask = mask
    
    
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
            if not self.L1IndexNameMap.has_key(seed):
                continue
            ps = L1Prescales[self.L1IndexNameMap[seed]]
            if ps:
                minPS = min(ps,minPS)
        if minPS==99999999999:
            return 0
        else:
            return minPS

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
        if self.HLT_Key == "":
            self.getRunInfo(runNumber)

        tmpcurs = self.getHLTCursor()
        sqlquery ="""
        select s.name, d.value from cms_hlt_gdr.u_confversions h, cms_hlt_gdr.u_pathid2conf a, cms_hlt_gdr.u_pathid2pae n, \
        cms_hlt_gdr.u_paelements b, cms_hlt_gdr.u_pae2moe c, cms_hlt_gdr.u_moelements d, cms_hlt_gdr.u_mod2templ e,cms_hlt_gdr.u_moduletemplates f,\
        cms_hlt_gdr.u_pathids p, cms_hlt_gdr.u_paths s where h.name='%s' and a.id_confver=h.id and  n.id_pathid=a.id_pathid and b.id=n.id_pae and\
        c.id_pae=b.id and d.id=c.id_moe and d.name='L1SeedsLogicalExpression' and e.id_pae=b.id and f.id=e.id_templ and f.name='HLTLevel1GTSeed' and\
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
        if self.GT_Key == "":
            self.getRunInfo(runNumber)
        
        AlgoNameQuery = """SELECT ALGO_INDEX, ALIAS FROM CMS_GT.L1T_MENU_ALGO_VIEW
        WHERE MENU_IMPLEMENTATION IN (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')
        ORDER BY ALGO_INDEX""" % (self.GT_Key,)
        try:
            self.curs.execute(AlgoNameQuery)
        except:
            print "Get L1 Name Index failed"
            return

        for index,name in self.curs.fetchall():
            name = stripVersion(name)
            self.L1IndexNameMap[name] = index

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
            if self.GT_Key == "": self.getRunInfo(runNumber)
            sqlquery = """SELECT ALGO_INDEX FROM CMS_GT.L1T_MENU_ALGO_VIEW
            WHERE ALIAS ='%s' AND MENU_IMPLEMENTATION IN
            (SELECT L1T_MENU_FK FROM CMS_GT.GT_SETUP WHERE ID='%s')""" % (pathName,self.GT_Key)
            
            try:
                self.curs.execute(sqlquery)
                bitNum, = self.curs.fetchone()
                url = "https://cmswbm.web.cern.ch/cmswbm/cmsdb/servlet/ChartL1TriggerRates?fromTime=&toTime=&fromLSNumber=&toLSNumber=&minRate=&maxRate=&minCount=&maxCount=&postDeadRates=1&drawCounts=0&drawLumisec=1&runID=%s&bitID=%s&type=0&TRIGGER_NAME=%s&LSLength=23.310409580838325" % (runNumber,bitNum,pathName)
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
