#######################################################)
# File: ShiftMonitorTool.py
# Author: Nathaniel Carl Rupprecht Charlie Mueller Alberto Zucchetta
# Date Created: July 13, 2015
#
# Dependencies: DBParser.py, mailAlert.py
#
# Data Type Key:
#    { a, b, c, ... }    -- denotes a tuple
#    [ key ] <object>  -- denotes a dictionary of keys associated with objects
#    ( object )          -- denotes a list of objects
#######################################################

# Imports
import ROOT
import sys, os
import copy
import time
import datetime
import pickle
import json
import requests
import yaml
import getopt # command line options
from colors import bcolors # colors

# Database parser
import DBParser

# For alerts
from Alerts import AlertLevel, PriorityAlert, MultipleAlert, MattermostMessage, AudioMessage, OnScreenMessage, RateAlert 
from Logger import Logger
from FitFinder import FitFinder
from OIDCAuth import OIDCAuth
from mattermostAlert import mattermostAlert
from audioAlert import audioAlert

accessPrometheus_ = False
try:
    from prometheus_client import Gauge, CollectorRegistry, write_to_textfile
    accessPrometheus_ = True
except ModuleNotFoundError:
    print("No Prometheus client found. Skipping import.")
    
# --- 13 TeV constant values ---
ppInelXsec   = 80000.   # 80 mb
orbitsPerSec = 11245.8  # Hz
lsLength     = 23.3104  # s = 2^18 / orbitsPerSec

# Use: Writes a string in a fixed length margin string (pads with spaces)
def stringSegment(string, width):
    if width > 0:
        return '{:{width}}'.format(string, width=width)
    elif width == 0:
        return string
    else:
        return '{:>{width}}'.format(string, width=abs(width))

# Alias for sys.stdout.write
sys.stdout = Logger()
write = sys.stdout.write

# Class ShiftMonitor
class ShiftMonitor:

    PROTECTED = ['redoTList',
            'redoTList',
            'lastRunNumber',
            'lumi_ave',
            'normal',
            'pu_ave',
            'isUpdating',
            'simulate',
            'currentLS',
            'mattermostSendTime',
            'bad',
            'runNumber',
            'totalStreams',
            'lastLS',
            'triggerMode',
            'InputFitHLT',
            'badRates',
            'deadTimeData',
            'l1rateData',
            'InputFitL1',
            'LSRange',
            'usableHLTTriggers',
            'numBunches',
            'lumiData',
            'LHCStatus',
            'otherHLTTriggers',
            'usableL1Triggers',
            'otherL1Triggers',
            'mailTriggers',
            'triggerList',
            'HLTRates',
            'parser',
            'l1t_rate_alert',
            'L1Rates',
            'FitFinder',
            'Rates',
            'startLS',
            'header',
            'spacing',
            'tableData',
            'pdData',
            'run_type',
            'streamData',
            'gauge_luminosity',
            'gauge_observed_trigger_rate',
            'gauge_predicted_trigger_rate']


    def __init__(self, accessPrometheus=accessPrometheus_):
        self.FitFinder = FitFinder()

        # Suppress root warnings
        ROOT.gErrorIgnoreLevel = 7000

        # Fits and fit files
        self.fitFile =                  "Fits/{runType}/referenceFits_{runType}_monitored.pkl" # The fit file, can contain both HLT and L1 triggers
        self.InputFitHLT = None         # The fit information for the HLT triggers
        self.InputFitL1 = None          # The fit information for the L1 triggers

        # DBParser
        self.parser = DBParser.DBParser()   # A database parser

        # Rates
        self.HLTRates = None            # HLT rates
        self.L1Rates = None             # L1 rates
        self.Rates = None               # Combined L1 and HLT rates
        self.deadTimeData = {}          # initializing deadTime dict

        # Run control
        self.lastRunNumber = -2         # The run number during the last segment
        self.runNumber = -1             # The number of the current run
        self.numBunches = [-1, -1]      # Number of [target, colliding] bunches
        self.LHCStatus = ["",0]         # First element is the status string, second is the number of consecutive queries in this status
        self.simulation_runNumber = []  # Define a list of simulation runs
        self.runIndex = 0               # Run index used in simulation mode

        # Running over a previouly done run
        self.LSRange = [0,0]            # If we want to only look at a range of LS from the run
        self.simulate = False           # Simulate running through and monitoring a previous run

        # Lumisection control
        self.lastLS = 1                 # The last LS that was processed last segment
        self.currentLS = 1              # The latest LS written to the DB
        self.slidingLS = -1             # The number of LS to average over, use -1 for no sliding LS
        self.useLSRange = False         # Only look at LS in a certain range
        self.LS_increment = 3

        # Mode
        self.triggerMode = None         # The trigger mode
        self.run_type = None            # Run type: collisions, collisionsHI, cosmics, circulating

        # Columns header
        self.displayRawRates = False    # display raw rates, to display raw rates, set = True
        self.pileUp = True              # derive expected rate as a function of the pileUp, and not the luminosity

        # Triggers
        self.triggerList_file =         "TriggerLists/monitorlist_{runType}.list" # Monitored trigger list placeholder 
        self.triggerList = []           # A list of all the L1 and HLT triggers we want to monitor
        self.userSpecTrigList = False   # User specified trigger list
        self.usableHLTTriggers = []     # HLT Triggers active during the run that we have fits for (and are in the HLT trigger list if it exists)
        self.otherHLTTriggers = []      # HLT Triggers active during the run that are not usable triggers
        self.usableL1Triggers = []      # L1 Triggers active during the run that have fits for (and are in the L1 trigger list if it exists)
        self.otherL1Triggers = []       # L1 Triggers active during that run that are not usable triggers
        self.redoTList = True           # Whether we need to update the trigger lists
        self.ignoreFile =               "TriggerLists/monitorlist_IGNORED.list"
        self.ignoreStrings = []         # List of ignored triggers, filled from the config file, alternative filling method in queryDatabase()

        # Restrictions
        self.removeZeros = False        # If true, we don't show triggers that have zero rate

        # Trigger behavior
        self.trgDevThresholds = {}      # Dictionary of trigger dev thresholds (can be modified using the config file)
        self.trgPerDiffThresholds = {}  # Dictionary of trigger percent diff thresholds (can be modified using the config file)
        #self.percAccept = 50.0         # The acceptence for % diff
        #self.devAccept = 5             # The acceptance for deviation
        self.streamThresholds = {}      # Dictionary of stream thresholds [stream name] { threshold 0 (critical), threshold 1 (alert), threshold 2 (warning)}
        self.datasetThresholds = {}     # Dictionary of dataset thresholds [dataset name] { threshold 0 (critical), threshold 1 (alert), threshold 2 (warning)}
        self.percAcceptDefault = 50.0   # The default acceptence for % diff
        self.devAcceptDefault = 5       # The default acceptance for deviation
        self.badRates = {}              # A dictionary: [ trigger name ] { num consecutive bad , whether the trigger was bad last time we checked, rate, expected, dev }
        #self.recordAllBadTriggers = {} # A dictionary: [ trigger name ] < total times the trigger was bad > # Apparently never used?
        self.badStreams = {}            # A dictionary: [stream name] {LS, rate, size, bandwidth}
        self.badDatasets = {}           # A dictionary: [dataset name] {LS, rate}
        self.maxCBR = 5                 # The maximum consecutive db queries a trigger is allowed to deviate from prediction by specified amount before it's printed out
        self.displayBadRates = -1       # The number of bad rates we should show in the summary. We use -1 for all
        self.usePerDiff = False         # Whether we should identify bad triggers by perc diff or deviatoin
        self.sortRates = True           # Whether we should sort triggers by their rates
        self.maxHLTRate = 5000          # The maximum prescaled rate we allow an HLT Trigger to have (for heavy-ions)
        self.maxL1Rate = 50000          # The maximum prescaled rate we allow an L1 Trigger to have (for heavy-ions)
       
        # Streams and Datasets
        auth_file = open(str('OMSConfig.yaml'), 'r')
        self.auth_cfg = yaml.safe_load(auth_file)
        self.thresholdURL = "https://hltsupervisor.app.cern.ch/api/v0/thresholds"
        self.missingStreamThresholds = []  # List of streams (if any) that don't have a threshold in self.streamThresholds 
        self.missingDatasetThresholds = [] # List of datasets (if any) that don't have a threshold in self.datasetThresholds
        self.query_error = False        # If there is a query error, this is set to true and a message is sent during the next Mattermost alert
        self.dataset_error = False      # If there is a dataset error, this is set to true and a message is sent during the next Mattermost alert
        self.streams_error = False      # If there is a stream error, this is set to true and a message is sent during the next Mattermost alert

        # Mattermost Options
        self.mattermostTriggers = []    # A list of triggers that we should mail alerts about
        self.mattermostPeriod = 5*60      # Lenght of time inbetween emails
        self.mattermostSendTime = 0     # Time at which last email was sent
        self.mattermostTriggersSum = 0  # Number of trigger alerts sent to MM during current run

        self.configFilePath = ""        # Path to the config file
        self.lastCfgFileAccess = 0      # The last time the configuration file was updated

        self.l1rateData = {}
        self.lumiData = []
        # Save run info for report
        self.saveRunNumber = 1
        self.saveLS = 1
        self.saveTriggerMode = None
        self.saveLumi_ave = 0
        self.savePu_ave = 0
        self.saveLumiData = []

        l1_critical_rate_alert = RateAlert(
          message   = 'critical Level 1 Trigger rate',
          details   = '''
Please check that all detectors are behaving correctly.
Total Level 1 Trigger rate: {total:.1f} kHz
''',
          level     = AlertLevel.ERROR,
          measure   = lambda rates: rates['total'] / 1000.,             # convert from Hz to kHz
          threshold = 200., # kHz
          period    = 120., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        l1_high_rate_alert = RateAlert(
          message   = 'high Level 1 Trigger rate',
          details   = '''
Please check the prescale column.
Total Level 1 Trigger rate: {total:.1f} kHz
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['total'] / 1000.,             # convert from Hz to kHz
          threshold = 105., # kHz
          period    = 600., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        l1_total_rate_alert = PriorityAlert(l1_critical_rate_alert, l1_high_rate_alert)

        # from fill 6315, the expected rates for L1_SingleMu22 are
        #    7.7 kHz at 1.52e34 (pileup 58)
        #   11.7 kHz at 2.15e34 (pileup 82)
        l1_singlemu_rate_alert = RateAlert(
          message   = 'critical Level 1 Muon Trigger rate',
          details   = '''
Please check that the muon detectors and muon trigger are behaving correctly.
L1_SingleMu22:         {L1_SingleMu22:.1f} kHz
L1_SingleMu22_BMTF:    {L1_SingleMu22_BMTF:.1f} kHz
L1_SingleMu22_OMTF:    {L1_SingleMu22_OMTF:.1f} kHz
L1_SingleMu22_EMTF:    {L1_SingleMu22_EMTF:.1f} kHz
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['L1_SingleMu22'] / 1000.,     # convert from Hz to kHz
          threshold =  20., # kHz
          period    = 600., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        # from fill 6315, the expected rates for L1_SingleEG40 are
        #   11.7 kHz at 1.52e34 (pileup 58)
        #   18.2 kHz at 2.15e34 (pileup 82)
        l1_singleeg_rate_alert = RateAlert(
          message   = 'critical Level 1 EGamma Trigger rate',
          details   = '''
Please check that ECAL and the calorimetric trigger are behaving correctly.
L1_SingleEG40:         {L1_SingleEG40:.1f} kHz
L1_SingleIsoEG40:      {L1_SingleIsoEG40:.1f} kHz
L1_SingleIsoEG40er2p1: {L1_SingleIsoEG40er2p1:.1f} kHz
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['L1_SingleEG40'] / 1000.,     # convert from Hz to kHz
          threshold =  25., # kHz
          period    = 600., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        # from fill 6315, the expected rates for L1_SingleJet200 are
        #    2.3 kHz at 1.52e34 (pileup 58)
        #    4.2 kHz at 2.15e34 (pileup 82)
        l1_singlejet_rate_alert = RateAlert(
          message   = 'critical Level 1 Jet trigger rate',
          details   = '''
Please check that calorimeters and the calorimetric trigger are behaving correctly.
L1_SingleJet200:       {L1_SingleJet200:.1f} kHz
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['L1_SingleJet200'] / 1000.,   # convert from Hz to kHz
          threshold =  10., # kHz
          period    = 600., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        # from fill 6315, the expected rates for L1_ETM120 are
        #    6.2 kHz at 1.52e34 (pileup 58)
        #  105.  kHz at 2.15e34 (pileup 82)
        l1_centralmet_rate_alert = RateAlert(
          message   = 'critical Level 1 Missing Energy trigger rate',
          details   = '''
Please check that calorimeters and the calorimetric trigger are behaving correctly.
L1_ETM120:             {L1_ETM120:.1f} kHz
L1_ETMHF120:           {L1_ETMHF120:.1f} kHz
L1_ETMHF120_HTT60er:   {L1_ETMHF120_HTT60er:.1f} kHz
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['L1_ETM120'] / 1000.,         # convert from Hz to kHz
          threshold =  50., # kHz
          period    = 600., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        # from fill 6315, the expected rates for L1_ETMHF120 are
        #    7.0 kHz at 1.52e34 (pileup 58)
        #  109.  kHz at 2.15e34 (pileup 82)
        l1_formwardmet_rate_alert = RateAlert(
          message   = 'critical Level 1 Missing Energy trigger rate',
          details   = '''
Please check that HF and the calorimetric trigger are behaving correctly.
L1_ETM120:             {L1_ETM120:.1f} kHz
L1_ETMHF120:           {L1_ETMHF120:.1f} kHz
L1_ETMHF120_HTT60er:   {L1_ETMHF120_HTT60er:.1f} kHz
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['L1_ETMHF120'] / 1000.,       # convert from Hz to kHz
          threshold =  50., # kHz
          period    = 600., # s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        # set upper threshold for the L1 bit that monitor Laser Misfires for HCAL
        l1_hcalLaserMisfires_rate_alert = RateAlert(
          message   = 'high rate of HCAL laser misfire',
          details   = '''
Plase check the rate of L1_HCAL_LaserMon_Veto and contact the HCAL DoC
''',
          level     = AlertLevel.WARNING,
          measure   = lambda rates: rates['L1_HCAL_LaserMon_Veto'],     # thresholds are in Hz
          threshold =  100., #Hz
          period    = 600., #s
          actions   = [MattermostMessage, AudioMessage, OnScreenMessage] )

        l1_met_rate_alert = PriorityAlert(l1_centralmet_rate_alert, l1_formwardmet_rate_alert)

        self.l1t_rate_alert = MultipleAlert(
          l1_total_rate_alert,
          l1_singlemu_rate_alert,
          l1_singleeg_rate_alert,
          l1_singlejet_rate_alert,
          l1_hcalLaserMisfires_rate_alert,
          l1_met_rate_alert )

        # Other options
        self.quiet = False                      # Prints fewer messages in this mode
        self.noColors = False                   # Special formatting for if we want to dump the table to a file
        self.sendMattermostAlerts_static = True # Whether we should send alert to mattermost
        self.sendMattermostAlerts_dynamic = self.sendMattermostAlerts_static
        self.sendAudioAlerts = False            # Whether we should send audio warning messages in the control room (CAUTION)
        self.isUpdating = True                  # flag to determine whether or not we're receiving new LS
        self.showStreams = False                # Whether we should print stream information
        self.showPDs = False                    # Whether we should print pd information
        self.totalStreams = 0                   # The total number of streams
        self.maxStreamRate = 1000000            # The maximum rate we allow a "good" stream to have
        self.maxPDRate = 250                    # The maximum rate we allow a "good" pd to have
        self.lumi_ave = 0
        self.pu_ave = 0
        self.runPu_ave = 0
        self.runLumi_ave = 0
	#self.count_list = []
        #self.deadTimeCorrection = True         # correct the rates for dead time
        self.scale_sleeptime = 0.5              # Scales the length of time to wait before sending another query (1.0 = 60sec, 2.0 = 120sec, etc)
        self.scale_sleeptime_simulate = 0.05    # Shorter sleep period if in simulate mode

        # Gauges for prometheus client
        self.accessPrometheus = accessPrometheus
        if self.accessPrometheus:
            self.gauge_luminosity = Gauge('luminosity', 'Luminosity')
            self.gauge_observed_trigger_rate  = Gauge('ratemon_observed_trigger_rate',  'Observed trigger rate',  ["trigger"])
            self.gauge_predicted_trigger_rate = Gauge('ratemon_predicted_trigger_rate', 'Predicted trigger rate', ["trigger"])

    # Use: Opens a file containing a list of trigger names and adds them to the RateMonitor class's trigger list
    # Note: We do not clear the trigger list, this way we could add triggers from multiple files to the trigger list
    # -- fileName: The name of the file that trigger names are contained in
    # Returns: (void)
    def loadTriggersFromFile(self, fileName):
        try:
            file = open(fileName, 'r')
        except:
            print("File", fileName, "(a trigger list file) failed to open.")
            return
        allTriggerNames = file.read().split() # Get all the words, no argument -> split on any whitespace
        TriggerList = []
        for triggerName in allTriggerNames:
            # Recognize comments
            if triggerName[0] == '#': continue
            try:
                if not str(triggerName) in TriggerList:
                    TriggerList.append(DBParser.stripVersion(str(triggerName)))
            except:
                print("Error parsing trigger name in file", fileName)
        return TriggerList


    # Use: Get thresholds for streams and datasets from hltsupervisor, which is updated 
    # by HLTDocs. If the authentication and query are successful, the stream and dataset
    # threshold dictionaries are updated. If unsuccessful, they are left at their previous value
    # Returns: (void)
    def getThresholds(self):
        try: 
            # CERN authentication needed to query hltsupervisor
            hltsuperauth = OIDCAuth(
                client_id = self.auth_cfg['token_info']['token_name'],
                client_secret = self.auth_cfg['token_info']['token_secret'],
                audience="cms-tsg-frontend-client",    
                auth_url='https://auth.cern.ch/auth/realms/cern/api-access/token',
                cert_verify=True
            )
        
            # query to get dictionary of thresholds, update the thresholds dictionaries 
            url = self.thresholdURL
            rep = requests.get(url,headers=hltsuperauth.headers())
            if rep.status_code==200: 
                thresholds_json = rep.json()
                self.streamThresholds = thresholds_json['streams']
                self.datasetThresholds = thresholds_json['datasets']
            else: 
                self.query_error = True
        except: 
            self.query_error = True


    # Use: Formats the header string
    # Returns: (void)
    def getHeader(self):
        # Define spacing and header
        maxNameHLT = 0
        maxNameL1 = 0
        if len(self.usableHLTTriggers)>0 or len(self.otherHLTTriggers)>0:
            maxNameHLT = max([len(trigger) for trigger in self.usableHLTTriggers+self.otherHLTTriggers])
        if len(self.usableL1Triggers)>0 or len(self.otherL1Triggers)>0:
            maxNameL1 = max([len(trigger) for trigger in self.usableL1Triggers+self.otherL1Triggers])

        # Make the name spacing at least 90
        maxName = max([maxNameHLT, maxNameL1, 90])

        self.spacing = [maxName + 5, 14, 14, 14, 14, 14, 0]
        self.spacing[5] = max( [ 181 - sum(self.spacing), 0 ] )

        self.header = ""                # The table header
        self.header += stringSegment("* TRIGGER NAME", self.spacing[0])
        if (self.displayRawRates): self.header += stringSegment("* RAW [Hz]", self.spacing[1])
        else: self.header += stringSegment("* ACTUAL [Hz]", self.spacing[1])
        self.header += stringSegment("* EXPECTED", self.spacing[2])
        self.header += stringSegment("* % DIFF", self.spacing[3])
        self.header += stringSegment("* DEVIATION", self.spacing[4])
        self.header += stringSegment("* AVE PS", self.spacing[5])
        self.header += stringSegment("* COMMENTS", self.spacing[6])
        self.hlength = 181 #sum(self.spacing)

    # Use: Runs the program
    # Returns: (void)
    def run(self):

        # Run number
        if not self.simulate:
            self.runNumber, _, _, _ = self.parser.getLatestRunInfo()
        if self.simulate:
            self.runNumber = self.simulation_runNumber[self.runIndex]

        print("The current run number is %s." % (self.runNumber))

        self.setRunType()

        # Load the fit and trigger list
        if self.fitFile != "":
            inputFit = self.loadFit(self.fitFile.format(runType = self.run_type))
            fits_format = None
            for triggerName in list(inputFit.keys()):
                if type(inputFit[triggerName]) is list:
                    fits_format = 'dict_of_lists'
                elif type(inputFit[triggerName]) is dict:
                    fits_format = 'nested_dict'
                else:
                    fits_format = None
            if fits_format == 'dict_of_lists':
                for triggerName in list(inputFit.keys()):
                    if triggerName[0:3] == "L1_":
                        if self.InputFitL1 is None: self.InputFitL1 = {}
                        self.InputFitL1[DBParser.stripVersion(triggerName)] = inputFit[triggerName]
                    elif triggerName[0:4] == "HLT_":
                        if self.InputFitHLT is None: self.InputFitHLT = {}
                        self.InputFitHLT[DBParser.stripVersion(triggerName)] = inputFit[triggerName]
            if fits_format == 'nested_dict':
                for triggerName in list(inputFit.keys()):
                    best_fit_type, best_fit = self.FitFinder.getBestFit(inputFit[triggerName]) #best_fit=['best_fit_type',#,#,etc]
                    if triggerName[0:3] == "L1_":
                        if self.InputFitL1 is None: self.InputFitL1 = {}
                        self.InputFitL1[DBParser.stripVersion(triggerName)] = best_fit
                    elif triggerName[0:4] == "HLT_":
                        if self.InputFitHLT is None: self.InputFitHLT = {}
                        self.InputFitHLT[DBParser.stripVersion(triggerName)] = best_fit

        # Run as long as we can
        self.redoTList = True
        while True:
            try:
                # Check if we are still in the same run, get trigger mode
                self.lastRunNumber = self.runNumber
                self.saveRunInfo()
                if not self.simulate:
                    self.runNumber, _, _, _ = self.parser.getLatestRunInfo()
                if self.simulate:
                    self.runNumber = self.simulation_runNumber[self.runIndex]
                self.runLoop()
                self.runMail()
                self.sleepWait()
                if self.simulate:
                    # In simulate, go to the next run number when there are no more LS to print out
                    if self.currentLS - self.lastLS == 0:
                        if len(self.simulation_runNumber) - self.runIndex > 1:
                            self.runIndex += 1
                        elif len(self.simulation_runNumber) - self.runIndex == 1:
                            self.sendReport()
                            break
            except KeyboardInterrupt:
                print("Quitting. Bye.")
                break

    # Use: The main body of the main loop, checks the mode, creates trigger lists, prints table
    # Returns: (void)
    def runLoop(self):
        # Reset counting variable
        self.normal = 0
        self.bad = 0

        curr_LHC_status = self.parser.getLHCStatus()
        if curr_LHC_status != self.LHCStatus[0]:
            self.LHCStatus[0] = curr_LHC_status
            self.LHCStatus[1] = 1
        else:
            self.LHCStatus[1] += 1

        if self.simulate:
            self.LHCStatus[0] = 'Stable'
            self.LSRange[0] = self.currentLS
            self.LSRange[1] = self.currentLS + self.LS_increment
        # If we are using a configuration file to update options
        if self.configFilePath != "":
            self.updateOptions()

        # Get Rates: [triggerName][LS] { raw rate, prescale }
        self.queryDatabase()

        self.getThresholds()
        self.checkForBadStreams()
        self.checkForBadDatasets()
        self.checkForBadTriggers()
        self.checkTriggers()

        if "collisions" in self.run_type and (len(self.usableHLTTriggers) == 0 or len(self.usableL1Triggers) == 0):
            # On a new run start, not always able to get the full list of triggers --> Re-try until we have some
            self.redoTList = True

        # If we have started a new run
        if self.lastRunNumber != self.runNumber:
            # Send report for the last run
            self.sendReport()
            print("Starting a new run: Run %s" % (self.runNumber))
            self.lastLS = 0
            self.currentLS = 1
            # Check what mode we are in
            self.setRunType()
            self.redoTList = True
            self.mattermostTriggersSum = 0
            self.run_lumi_ave = []
	    #self.run_pu_ave = []

        #if self.simulate:
        #    self.LHCStatus[0] = 'Stable'
        #    self.LSRange[0] = self.currentLS
        #    self.LSRange[1] = self.currentLS + self.LS_increment

        #if self.simulate:
        #    self.LHCStatus[0] = 'Stable'
        #    self.LSRange[0] = self.currentLS
        #    self.LSRange[1] = self.currentLS + self.LS_increment

        # Construct (or reconstruct) trigger lists
        if self.redoTList:
            self.redoTriggerLists()

        # Make sure there is info to use
        if len(self.HLTRates) == 0 and len(self.L1Rates) == 0:
            print("No new information can be retrieved. Waiting... (There may be no new LS, or run active may be false)")
            return

        # If there are lumisection to show, print info for them
        if self.currentLS > self.lastLS:
            self.printTable()
        elif self.simulate:
            print(self.runNumber)
            self.printTable()
            return

            #raise KeyboardInterrupt
        else:
            print("Not enough lumisections. Last LS was %s, current LS is %s. Waiting." % (self.lastLS, self.currentLS))

        #self.dumpTriggerThresholds(self.triggerList, self.lumi_ave, 'test_json.json')

    def getRunType(self, runNumber):
        try:
            triggerMode = self.parser.getTriggerMode(runNumber)
        except:
            triggerMode = "other"

        if triggerMode.find("cosmics") > -1:
            runType = "cosmics"
        elif triggerMode.find("circulating") > -1:
            runType = "circulating"
        elif triggerMode.find("collisions") > -1:
            if self.parser.getFillType(runNumber).find("IONS") > -1:
                runType = "collisionsHI" # heavy-ion collisions
            else:
                runType = "collisions" # p-p collisions
        elif triggerMode == "MANUAL":
            runType = "MANUAL"
        elif triggerMode.find("highrate") > -1:
            runType = "other"
        else: runType = "other"

        return runType

    def setRunType(self):
        self.sendMattermostAlerts_dynamic = self.sendMattermostAlerts_static
        try:
            self.triggerMode = self.parser.getTriggerMode(self.runNumber)
        except:
            self.triggerMode = "other"
        
        self.run_type = self.getRunType(self.runNumber)

        if self.run_type == "other":
            self.sendMattermostAlerts_dynamic = False

    # Use: Remakes the trigger lists
    def redoTriggerLists(self):
        self.redoTList = False
        # Reset the trigger lists
        self.usableHLTTriggers = []
        self.otherHLTTriggers = []
        self.usableL1Triggers = []
        self.otherL1Triggers = []
        # Reset bad rate records
        self.badRates = {}           # A dictionary: [ trigger name ] { num consecutive bad, trigger bad last check, rate, expected, dev }
        # Set trigger lists automatically based on mode
        if not self.userSpecTrigList:
            if self.run_type in ["collisions", "collisionsHI", "cosmics"]:
                self.triggerList = self.loadTriggersFromFile(self.triggerList_file.format(runType = self.run_type.upper()))
                print("Monitoring triggers in: ", self.triggerList)
            elif self.run_type == "circulating":
                self.triggerList = self.loadTriggersFromFile(self.triggerList_file.format(runType = "COSMICS")) # circulating ~ cosmics 
                print("Monitoring triggers in: ", self.triggerList)
            else:
                self.triggerList = []
                print("No lists to monitor: trigger mode not recognized")

        # Re-make trigger lists
        if self.run_type == "cosmics":
           for trigger in list(self.triggerList):
                if trigger[0:4] == "HLT_":
                    #if trigger in self.InputFitHLT:
                    self.usableHLTTriggers.append(trigger)
                    #else:    
                        #self.otherHLTTriggers.append(trigger)
                if trigger[0:3] == "L1_":
                    #if trigger in self.InputFitL1:
                    self.usableL1Triggers.append(trigger)
                    #else:
                        #self.otherL1Triggers.append(trigger)
        else:
            for trigger in list(self.Rates.keys()):
                if trigger[0:4] == "HLT_" and self.InputFitHLT:
                    if trigger in self.InputFitHLT:
                        self.usableHLTTriggers.append(trigger)
                    else:
                        self.otherHLTTriggers.append(trigger)
                if trigger[0:3] == "L1_" and self.InputFitL1:
                    if trigger in self.InputFitL1:
                        self.usableL1Triggers.append(trigger)
                    else:
                        self.otherL1Triggers.append(trigger)
        self.getHeader()
    
    # Use: Gets the rates for the lumisections we want
    def queryDatabase(self):
        # Update lastLS
        self.lastLS = self.currentLS
        if not self.useLSRange:
            self.HLTRates = self.parser.getHLTRates(self.runNumber,[],self.lastLS)
            self.L1Rates = self.parser.getL1Rates(self.runNumber,self.lastLS,99999)
            try:
                self.streamData = self.parser.getStreamData(self.runNumber, self.lastLS)
                self.pdData = self.parser.getPrimaryDatasets(self.runNumber, self.lastLS)
            except:
                print("no stream or dataset")
        else:
            self.HLTRates = self.parser.getHLTRates(self.runNumber,[],self.LSRange[0],self.LSRange[1])
            self.L1Rates = self.parser.getL1Rates(self.runNumber,self.LSRange[0],self.LSRange[1])
            try:
                self.streamData = self.parser.getStreamData(self.runNumber, self.LSRange[0], self.LSRange[1])
                self.pdData = self.parser.getPrimaryDatasets(self.runNumber, self.LSRange[0], self.LSRange[1])
            except:
                print("no stream or dataset")
        try:
            self.totalStreams = len(list(self.streamData.keys()))
        except:
            print("no stream or dataset")
        self.Rates = {}
        self.Rates.update(self.HLTRates)
        self.Rates.update(self.L1Rates)
        lslist = []
        
        # Remove ignored triggers from list
        # Alternative way to fill self.ignoreStrings, by reading file 
        # self.ignoreStrings = self.loadTriggersFromFile(self.ignoreFile)
        for trig in list(self.Rates.keys()):
            isVetoed = False
            for vetoString in self.ignoreStrings:
                if trig.find(vetoString) > -1:
                    isVetoed = True
                    break
            if isVetoed:
                del self.Rates[trig]
                continue
            if len(self.Rates[trig]) > 0:
                lslist.append(max(self.Rates[trig]))

        # Update current LS
        if len(lslist) > 0: self.currentLS = max(lslist)

        self.isUpdating = (self.currentLS > self.lastLS)

        try:
            self.deadTimeData = self.parser.getDeadTime(self.runNumber)
        except:
            self.deadTimeData = {}
            print("Error getting deadtime data")

        try:
            self.l1rateData = self.parser.getL1rate(self.runNumber)
        except:
            self.l1rateData = {}
            print("Error getting total L1 rate data")

        self.lumiData = self.parser.getLumiInfo(self.runNumber, self.lastLS, self.currentLS)
        self.numBunches = self.parser.getNumberCollidingBunches(self.runNumber)

        # Calculate self.lumi_ave
        # TODO: Add avg deadtime and avg l1 rate calculations here
        aveLumi = 0
        runLumi_list = []
        self.count_list = []
        if self.run_type != "cosmics":
            # Find the average lumi since we last checked
            count = 0
            for LS, instLumi, psi, physics, all_subSys_good, pileup in self.lumiData:
                # If we are watching a certain range, throw out other LS
                if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
                # Average our instLumi
                if not instLumi is None and physics:
                    aveLumi += instLumi
                    count += 1
                    # Append all instLumi for overall run instLumi average calculation
                    if self.currentLS - self.lastLS == 3:
                        if count < 4:
                            runLumi_list.append(instLumi)
                    if self.currentLS - self.lastLS < 3 and self.currentLS - self.lastLS != 0 and self.lastLS != 0:
                        lumiLS_diff = self.currentLS - self.lastLS + 1
                        if count < lumiLS_diff:
                            runLumi_list.append(instLumi)
                    if self.currentLS == self.lastLS and self.lastLS != 0:
                        if count == 1:
                            runLumi_list.append(instLumi)
            if count == 0:
                aveLumi = 0
            else:
                aveLumi /= float(count)
        self.lumi_ave = aveLumi
        if len(runLumi_list) != 0:
            self.runLumi_ave = sum(runLumi_list)/len(runLumi_list)
        elif len(runLumi_list) == 0:
            self.runLumi_ave = 0

    # Use: Retrieves information and prints it in table form
    def printTable(self):
        if self.slidingLS == -1:
            self.startLS = self.lastLS
        else: self.startLS = max( [0, self.currentLS-self.slidingLS ] )+1

        aveL1rate = 0
        aveDeadTime = 0
        PScol = -1

        physicsActive = False # True if we have at least 1 LS with lumi and physics bit true
        if self.run_type != "cosmics":
            # Find the average lumi since we last checked
            count = 0
            # Get luminosity (only for non-cosmic runs)
            for LS, instLumi, psi, physics, all_subSys_good, pileup in self.lumiData:
                # If we are watching a certain range, throw out other LS
                if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
                # Average our instLumi
                if not instLumi is None:
                    physicsActive = physicsActive or physics
                    PScol = psi
                    if LS in self.deadTimeData: aveDeadTime += self.deadTimeData[LS]
                    else: aveDeadTime = 0
                    if LS in self.l1rateData: aveL1rate += self.l1rateData[LS]
                    else: aveL1rate = 0
                    count += 1
            if count == 0:
                expected = "NONE"
            else:
                aveDeadTime /= float(count)
                aveL1rate /= float(count)
        else:
            count = 0
            for LS in list(self.l1rateData.keys()):
                if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
                if LS in self.deadTimeData: aveDeadTime += self.deadTimeData[LS]
                else: aveDeadTime = 0
                if LS in self.l1rateData: aveL1rate += self.l1rateData[LS]
                else: aveL1rate = 0
                count += 1
            if not count == 0:
                aveDeadTime /= float(count)
                aveL1rate /= float(count)

        if self.numBunches[0] > 0 and not self.lumi_ave == 0:
            self.pu_ave = self.lumi_ave/self.numBunches[0]*ppInelXsec/orbitsPerSec
            self.runPu_ave = self.runLumi_ave/self.numBunches[0]*ppInelXsec/orbitsPerSec
        else:
            self.pu_ave = 0
            self.runPu_ave = 0
        # We only do predictions when there were physics active LS in a collisions run
        doPred = (physicsActive and "collisions" in self.run_type) or self.run_type == "cosmics"
        # Print the header
        self.printHeader()
        if "collisions" in self.run_type:
            # Print triggers from self.usableHLTTriggers, self.usableL1Triggers
            anytriggers = False
            if len(self.usableHLTTriggers) > 0:
                print('*' * self.hlength)
                print("Predictable HLT Triggers (ones we have a fit for)")
                print('*' * self.hlength)
                anytriggers = True
                self.printTableSection(self.usableHLTTriggers, doPred, self.lumi_ave)
            if len(self.usableL1Triggers) > 0:
                print('*' * self.hlength)
                print("Predictable L1 Triggers (ones we have a fit for)")
                print('*' * self.hlength)
                anytriggers = True
                self.printTableSection(self.usableL1Triggers, doPred, self.lumi_ave)
        else:
            # Print triggers from self.usableHLTTriggers, self.otherHLTTriggers, self.usableL1Triggers, self.otherL1Triggers
            anytriggers = False
            if len(self.usableHLTTriggers) > 0:
                print('*' * self.hlength)
                print("Predictable HLT Triggers (ones we have a fit for)")
                print('*' * self.hlength)
                anytriggers = True
                self.printTableSection(self.usableHLTTriggers, doPred, self.lumi_ave)
            if len(self.otherHLTTriggers) > 0:
                print('*' * self.hlength)
                print("Unpredictable HLT Triggers (ones we have no fit for or do not try to fit)")
                print('*' * self.hlength)
                anytriggers = True
                self.printTableSection(self.otherHLTTriggers, False, self.lumi_ave)
            if len(self.usableL1Triggers) > 0:
                print('*' * self.hlength)
                print("Predictable L1 Triggers (ones we have a fit for)")
                print('*' * self.hlength)
                anytriggers = True
                self.printTableSection(self.usableL1Triggers, doPred, self.lumi_ave)
            if len(self.otherL1Triggers) > 0:
                print('*' * self.hlength)
                print("Unpredictable L1 Triggers (ones we have no fit for or do not try to fit)")
                print('*' * self.hlength)
                anytriggers = True
                self.printTableSection(self.otherL1Triggers, False, self.lumi_ave)
        if not anytriggers:
            print('*' * self.hlength)
            print("\n --- No useable triggers --- \n")
        # Print stream data
        if self.showStreams:
            print('*' * self.hlength)
            streamSpacing = [ 50, 20, 25, 25, 25, 25 ]
            head = stringSegment("* Stream name", streamSpacing[0])
            head += stringSegment("* NLumis", streamSpacing[1])
            head += stringSegment("* Events", streamSpacing[2])
            head += stringSegment("* Stream rate [Hz]", streamSpacing[3])
            head += stringSegment("* File size [GB]", streamSpacing[4])
            head += stringSegment("* Stream bandwidth [GB/s]", streamSpacing[5])
            print(head)
            print('*' * self.hlength)
            for name in sorted(self.streamData.keys()):
                count = 0
                streamsize = 0
                aveBandwidth = 0
                aveRate = 0
                for LS, rate, size, bandwidth in self.streamData[name]:
                    streamsize += size
                    aveRate += rate
                    aveBandwidth += bandwidth
                    count += 1
                if count > 0:
                    aveRate /= count
                    streamsize /= (count*1000000000.0)
                    aveBandwidth /= (count*1000000000.0)
                    row = stringSegment("* "+name, streamSpacing[0])
                    row += stringSegment("* "+str(int(count)), streamSpacing[1])
                    row += stringSegment("* "+str(int(aveRate*23.3*count)), streamSpacing[2])
                    row += stringSegment("* "+"{0:.2f}".format(aveRate), streamSpacing[3])
                    row += stringSegment("* "+"{0:.2f}".format(streamsize), streamSpacing[4])
                    row += stringSegment("* "+"{0:.5f}".format(aveBandwidth), streamSpacing[5])
                    if not self.noColors and aveRate > self.maxStreamRate and self.run_type != "other": write(bcolors.WARNING) # Write colored text
                    print(row)
                    if not self.noColors and aveRate > self.maxStreamRate and self.run_type != "other": write(bcolors.ENDC)    # Stop writing colored text
                else: pass
        # Print PD data
        if self.showPDs:
            print('*' * self.hlength)
            pdSpacing = [ 50, 20, 25, 25]
            head = stringSegment("* Primary Dataset name", pdSpacing[0])
            head += stringSegment("* NLumis", pdSpacing[1])
            head += stringSegment("* Events", pdSpacing[2])
            head += stringSegment("* Dataset rate [Hz]", pdSpacing[3])
            print(head)
            print('*' * self.hlength)
            for name in list(self.pdData.keys()):
                count = 0
                aveRate = 0
                for LS, rate in self.pdData[name]:
                    aveRate += rate
                    count += 1
                if count > 0:
                    aveRate /= count
                    row = stringSegment("* "+name, pdSpacing[0])
                    row += stringSegment("* "+str(int(count)), pdSpacing[1])
                    row += stringSegment("* "+str(int(aveRate*23.3*count)), pdSpacing[2])
                    row += stringSegment("* "+"{0:.2f}".format(aveRate), pdSpacing[3])
                    if not self.noColors and aveRate > self.maxPDRate and self.run_type != "other": write(bcolors.WARNING) # Write colored text
                    print(row)
                    if not self.noColors and aveRate > self.maxPDRate and self.run_type != "other": write(bcolors.ENDC)    # Stop writing colored text
                else: pass

        # Closing information
        print('*' * self.hlength)
        print("SUMMARY:")
        if "collisions" in self.run_type: print("Triggers in Normal Range: %s   |   Triggers outside Normal Range: %s" % (self.normal, self.bad))
        if "collisions" in self.run_type:
            print("Prescale column index:", end=' ')
            if PScol == 0:
                if not self.noColors and PScol == 0 and self.run_type != "other": write(bcolors.WARNING) # Write colored text
                print(PScol, "\t0 - Column 0 is an emergency column in collision mode, please select the proper column")
                if not self.noColors and PScol == 0 and self.run_type != "other": write(bcolors.ENDC)    # Stop writing colored text
            else:
                print(PScol)
        try:
            print("Average inst. lumi: %.0f x 10^30 cm-2 s-1" % (self.lumi_ave))
        except:
            print("Average inst. lumi: Not available")
        print("Total L1 rate: %.0f Hz" % (aveL1rate))
        print("Average dead time: %.2f %%" % (aveDeadTime))
        try:
            print("Average PU: %.2f" % (self.pu_ave))
        except:
            print("Average PU: %s" % (self.pu_ave))
        print('*' * self.hlength)

        # Print the list of triggers that are out of line
        if self.displayBadRates != 0:
            count = 0
            if self.displayBadRates != -1: write("First %s triggers that are bad: " % (self.displayBadRates))
            elif len(self.badRates) > 0 : write("All triggers deviating past thresholds from fit and/or L1 rate > %s Hz, HLT rate > %s Hz: " %(self.maxL1Rate,self.maxHLTRate))
            for trigger in self.badRates:
                if self.badRates[trigger][1]:
                    count += 1
                    write(trigger)
                    if count != self.displayBadRates-1:
                        write(", ")
                if count == self.displayBadRates:
                    write(".....")
                    break
            print("")

    # Use: Prints the table header
    def printHeader(self):
        print("\n\n", '*' * self.hlength)
        print("INFORMATION:")
        print("Run Number: %s" % (self.runNumber))
        print("LS Range: %s - %s" % (self.startLS, self.currentLS))
        print("Latest LHC Status: %s" % (self.LHCStatus[0]))
        print("Number of Colliding Bunches: %s" % self.numBunches[0])
        print("Trigger Mode (Run Type): %s (%s)" % (self.triggerMode, self.run_type))
        print("Number of HLT Triggers: %s \nNumber of L1 Triggers: %s" % (len(list(self.HLTRates.keys())) , len(list(self.L1Rates.keys()))))
        print("Number of Streams:", self.totalStreams)
        print('*' * self.hlength)
        print(self.header)

    # Use: Prints a section of a table, ie all the triggers in a trigger list (like usableHLTTriggers, otherHLTTriggers, etc)
    def printTableSection(self, triggerList, doPred, aveLumi=0, maxRows=25):
        # A list of tuples, each a row in the table: ( { trigger, rate, predicted rate, sign of % diff, abs % diff, sign of sigma, abs sigma, ave PS, comment } )
        
        self.tableData = []

        # Get the trigger data
        for trigger in triggerList: self.getTriggerData(trigger, doPred, aveLumi)

        # Sort
        # Note: Since tup[4] can be a float or an empty str, avoid TypeError by creating tuple where first element
        # is True of False (based on whether or not tup[4] is a str), second is 0 or tup[4] and sort that tuple instead
        if doPred:
            # [4] is % diff, [6] is deviation
            if self.usePerDiff:
                #self.tableData.sort(key=lambda tup : tup[4], reverse = True)
                self.tableData.sort(key=lambda tup : ( isinstance(tup[4],str) , tup[4] if not isinstance(tup[4],str) else 0 ) , reverse = True)
            else:
                #self.tableData.sort(key=lambda tup : tup[6], reverse = True)
                self.tableData.sort(key=lambda tup : ( isinstance(tup[6],str) , tup[6] if not isinstance(tup[6],str) else 0 ) , reverse = True)
        elif self.sortRates:
            #self.tableData.sort(key=lambda tup: tup[1], reverse = True)
            self.tableData.sort(key=lambda tup : ( isinstance(tup[1],str) , tup[1] if not isinstance(tup[1],str) else 0 ) , reverse = True)

        nRows = 0
        for trigger, rate, pred, sign, perdiff, dsign, dev, avePS, comment in self.tableData:
            if nRows > maxRows:
                break
            if "collisions" not in self.run_type and rate == 0:
                # When not in collisions mode, ignore triggers with 0 rate
                continue

            info  = stringSegment("* "+trigger, self.spacing[0])
            info += stringSegment("* "+"{0:.2f}".format(rate), self.spacing[1])

            # Prediction Column
            if pred != "":
                info += stringSegment("* "+"{0:.2f}".format(pred), self.spacing[2])
            else:
                info += stringSegment("", self.spacing[2])

            # % Diff Column
            if perdiff == "":
                info += stringSegment("", self.spacing[3])
            elif perdiff == "INF":
                info += stringSegment("* INF", self.spacing[3])
            else:
                info += stringSegment("* "+"{0:.2f}".format(sign*perdiff), self.spacing[3])

            # Deviation Column
            if dev == "":
                info += stringSegment("", self.spacing[4])
            elif dev == "INF" or dev == ">1E6":
                info += stringSegment("* "+dev, self.spacing[4])
            else:
                info += stringSegment("* "+"{0:.2f}".format(dsign*dev), self.spacing[4])

            info += stringSegment("* "+"{0:.2f}".format(avePS), self.spacing[5])
            info += stringSegment("* "+comment, self.spacing[6])

            # Color the bad triggers with warning colors
            trgAcceptThreshold = self.findTrgThreshold(trigger) # Check for non default thresholds
            if avePS != 0 and self.isBadTrigger(perdiff, dev, rate, trigger[0:3]=="L1_",trgAcceptThreshold):
            #if avePS != 0 and self.isBadTrigger(perdiff, dev, rate, trigger[0:3]=="L1_"):
                if not self.noColors and self.run_type != "other": write(bcolors.WARNING) # Write colored text
                print(info)
                if not self.noColors and self.run_type != "other": write(bcolors.ENDC)    # Stop writing colored text
            # Don't color normal triggers
            else:
                print(info)
            nRows += 1

    # Use: Returns whether a given trigger is bad
    # Returns: Whether the trigger is bad
    #def isBadTrigger(self, perdiff, dev, psrate, isL1):
    def isBadTrigger(self, perdiff, dev, psrate, isL1, trgAcceptThreshold):
        if psrate == 0: return False
        if self.run_type == "other": return False
        if self.usePerDiff:
            #if perdiff != "INF" and perdiff != "" and perdiff != None and abs(perdiff) > self.percAccept:
            if perdiff != "INF" and perdiff != "" and perdiff != None and abs(perdiff) > trgAcceptThreshold:
                return True
        else:
            #if dev != "INF" and dev != "" and dev != None and (dev == ">1E6" or abs(dev) > self.devAccept):
            if dev != "INF" and dev != "" and dev != None and (dev == ">1E6" or abs(dev) > trgAcceptThreshold):
                return True
        if isL1 and psrate > self.maxL1Rate:
            return True
        elif not isL1 and psrate > self.maxHLTRate:
            return True
        return False

    # Use: Gets a row of the table, self.tableData: ( { trigger, rate, predicted rate, sign of % diff, abs % diff, ave PS, comment } )
    # Parameters:
    # -- trigger : The name of the trigger
    # -- doPred  : Whether we want to make a prediction for this trigger
    # -- aveLumi : The average luminosity during the LS in question
    # Returns: (void)
    def getTriggerData(self, trigger, doPred, aveLumi):
        # In case of critical error (this shouldn't occur)
        if trigger not in self.Rates: return

        # If cosmics, don't do predictions
        # if self.run_type == "cosmics": doPred = False
        # Calculate rate
        if doPred:
            if not aveLumi is None:
                expected = self.calculateRate(trigger, aveLumi)
                if expected < 0: expected = 0                # Don't let expected value be negative
                avePSExpected = expected
                # Get the mean square error (standard deviation)
                mse = self.getMSE(trigger)
            else:
                expected = None
                avePSExpected = None
                mse = None
        # Find the ave rate since the last time we checked
        aveRate = 0
        properAvePSRate = 0
        avePS = 0
        count = 0
        comment = ""
        for LS in list(self.Rates[trigger].keys()):
            if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
            elif LS < self.startLS or LS > self.currentLS: continue

            prescale = self.Rates[trigger][LS][1]
            rate = self.Rates[trigger][LS][0]
            try:
                deadTime = self.deadTimeData[LS]
            except:
                # Unable to get deadtime for some LS
                deadTime = 0
            if trigger[0:3] != "L1_": rate *= 1. + (deadTime/100.)
            if prescale > 0: properAvePSRate += rate/prescale
            else: properAvePSRate += rate
            aveRate += rate
            count += 1
            avePS += prescale
        if count > 0:
            if aveRate == 0: comment += "0 counts "
            aveRate /= count
            properAvePSRate /= count
            avePS /= count
            if avePS == 0.0:
                comment = "PS=0"
                doPred = False
        else:
            comment += "No rate yet "
            doPred = False

        if doPred and not avePSExpected is None and avePS > 1: avePSExpected /= avePS
        if not doPred and self.removeZeros and aveRate == 0: return  # Returns if we are not making predictions for this trigger and we are throwing zeros

        # We want this trigger to be in the table
        row = [trigger]
        if self.displayRawRates:
            row.append(aveRate)
        else:
            row.append(properAvePSRate)
        if doPred and not expected is None: row.append(avePSExpected)
        else: row.append("") # No predicted rate
        # Find the % diff
        if doPred:
            if expected == "NONE":
                perc = "UNDEF"
                dev = "UNDEF"
                row.append(1)    # Sign of % diff
                row.append(perc) # abs % diff
                row.append(1)    # Sign of deviation
                row.append(dev)  # abs deviation
            else:
                diff = aveRate-expected
                if expected!=0:
                    perc = 100*diff/expected
                else:
                    perc = "INF"
                if mse!=0:
                    dev = diff/mse
                    if abs(dev)>1000000:
                        dev = ">1E6"
                else:
                    dev = "INF"
                # perc can be a str, in python2 "str">0 is True, for python3 we get a TypeError, so check if str before checking if >0
                if type(perc) is str:
                    sign=1
                else:
                    if perc>0:
                        sign=1
                    else:
                        sign=-1
                row.append(sign)       # Sign of % diff
                if perc!="INF":
                    row.append(abs(perc))  # abs % diff
                else:
                    row.append("INF")
                row.append(sign)       # Sign of the deviation
                if dev!="INF" and dev!=">1E6":
                    row.append(abs(dev))   # abs deviation
                else:
                    row.append(dev)
        else:
            row.append("") # No prediction, so no sign of a % diff
            row.append("") # No prediction, so no % diff
            row.append("") # No prediction, so no sign of deviation
            row.append("") # No prediction, so no deviation
        # Add the rest of the info to the row
        row.append(avePS)
        row.append(comment)

        self.tableData.append(row)

        # Add row to the table data
        if doPred:
            if expected > 0:
                self.tableData.append(row)
                if self.accessPrometheus:
                    self.gauge_observed_trigger_rate.labels(trigger=trigger).set(row[1])
                    self.gauge_predicted_trigger_rate.labels(trigger=trigger).set(row[2])
                    self.gauge_luminosity.set(aveLumi)
        else:
            self.tableData.append(row)

    # Use: Checks for bad triggers
    def checkForBadTriggers(self):
        # Check if physActive is true or false
        physActive = False
        for LS, instLumi, psi, physics, all_subSys_good, pileup in self.lumiData:
            if not instLumi is None and physics:
                physActive = True
                break
        for trigger, data in self.Rates.items():

            # Check if there is a non-default value for trigger threshold in the configuration file and set thresholds accordingly
            trgAcceptThreshold = self.findTrgThreshold(trigger)

            isMonitored = trigger in self.triggerList
            if self.InputFitHLT:
                hasFit = trigger in self.InputFitHLT
            elif self.InputFitL1:
                hasFit = trigger in self.InputFitL1
            else:
                hasFit = False
            hasLSRate = len(list(self.Rates[trigger].keys())) > 0 
            isNonZeroPS = sum([ v[1] for k,v in data.items() ]) > 0  
 
            doPred = hasFit and isMonitored and (self.run_type=="cosmics" or "collisions" in self.run_type)
            doPred = doPred and isNonZeroPS
            doPred = doPred and hasLSRate

            avePSExpected = properAvePSRate = expected = aveRate = avePS = count = mse = 0
            dev = perc = None
            # Calculate rate
            if doPred:
                if not self.lumi_ave is None:
                    expected = self.calculateRate(trigger, self.lumi_ave)
                    if expected < 0: expected = 0   # Don't let expected value be negative
                    avePSExpected = expected
                    mse = self.getMSE(trigger)      # Get the mean square error (standard deviation)
            # Find the ave rate since the last time we checked
            for LS in list(data.keys()):
                if self.useLSRange and (LS < self.LSRange[0] or LS > self.LSRange[1]): continue
                elif LS < self.lastLS or LS > self.currentLS: continue
                prescale = data[LS][1]
                rate = data[LS][0]
                try:
                    deadTime = self.deadTimeData[LS]
                except:
                    # Unable to get deadtime for some LS
                    deadTime = 0
                if trigger[0:3] != "L1_": rate *= 1. + (deadTime/100.)
                if prescale > 0: properAvePSRate += rate/prescale
                else: properAvePSRate += rate
                aveRate += rate
                count += 1
                avePS += prescale
            if count > 0:
                aveRate /= count
                properAvePSRate /= count
                avePS /= count
            if not doPred and self.removeZeros and aveRate == 0: continue  # Continues if we are not making predictions for this trigger and we are throwing zeros
            if doPred:
                if avePS > 1: avePSExpected /= avePS
                #if expected == "NONE":
                #    perc = "UNDEF"
                #    dev = "UNDEF"
                #else:
                #    diff = aveRate-expected
                #    if expected!=0: perc = 100*diff/expected
                #    else: perc = "INF"
                #    if mse!=0:
                #        dev = diff/mse
                #        if abs(dev)>1000000: dev = ">1E6"
                #    else: dev = "INF"
                if expected != 0: perc = 100*(aveRate - expected)/expected
                if mse != 0: dev = (aveRate - expected)/mse
                # Check for bad rates, comparing to reference fit
                if self.isBadTrigger(perc,dev,properAvePSRate,trigger[0:3]=="L1_",trgAcceptThreshold):
                    self.bad += 1
                    if trigger not in self.badRates:
                        self.badRates[trigger] = [1,True,properAvePSRate,avePSExpected,dev,avePS,True]
                    else:
                        # Record consecutive bad rates
                        last = self.badRates[trigger]
                        self.badRates[trigger] = [last[0]+1,True,properAvePSRate,avePSExpected,dev,avePS,True]
                else:
                    self.normal += 1
                    # Remove warning from badRates
                    if trigger in self.badRates:
                        del self.badRates[trigger]
            else:
                # Check for bad rates, comparing to hard cut offs
                if self.isBadTrigger(perc,dev,properAvePSRate,trigger[0:3]=="L1_",trgAcceptThreshold) and avePS > 0:
                    self.bad += 1
                    if trigger not in self.badRates:
                        #self.badRates[trigger] = [ 1, True, properAvePSRate, -999, -999, -999 ]
                        self.badRates[trigger] = [1,True,properAvePSRate,avePSExpected,dev,avePS,False]
                    else:
                        # Record consecutive bad rates
                        last = self.badRates[trigger]
                        #self.badRates[trigger] = [ last[0]+1, True, properAvePSRate, -999, -999, -999 ]
                        self.badRates[trigger] = [last[0]+1,True,properAvePSRate,avePSExpected,dev,avePS,False]
                else:
                    self.normal += 1
                    # Remove warning from badRates
                    if trigger in self.badRates and avePS > 0:
                        del self.badRates[trigger]

    # Use: Checks for bad streams
    def checkForBadStreams(self):
        physActive = False
        for LS, instLumi, psi, physics, all_subSys_good, pileup in self.lumiData:
            if not instLumi is None and physics:
                physActive = True
                break
        
        # loop through streams and if the rate is exceeding the threshold, add to the badDatasets dictionary
        for name in self.streamData.keys():
            empty_threshold = False
            
            self.badStreams[name]=[]
            for entry in self.streamData[name]:
                try: 
                    if entry[1]>self.streamThresholds[name][1]:
                        self.badStreams[name].append(entry)
                except:  
                    empty_threshold = True
            
            # if any of the streams don't have a threshold, add to the list of missing thresholds
            if empty_threshold == True: 
                self.missingStreamThresholds.append(name)
            # remove dictionary entries where none of the LS were bad
            if len(self.badStreams[name])==0:
                self.badStreams.pop(name)
        
    # Use: Checks for bad streams
    def checkForBadDatasets(self):
        physActive = False
        for LS, instLumi, psi, physics, all_subSys_good, pileup in self.lumiData:
            if not instLumi is None and physics:
                physActive = True
                break

        # loop through datasets and if the rate is exceeding the threshold, add to the badDatasets dictionary
        for name in self.pdData.keys():
            empty_threshold = False

            self.badDatasets[name]=[]
            for entry in self.pdData[name]:
                try: 
                    if entry[1]>self.datasetThresholds[name][1]:
                        self.badDatasets[name].append(entry)
                except: 
                    empty_threshold = True
            # if any of the datasets don't have a threshold, add to the list of missing thresholds
            if empty_threshold == True: 
                self.missingDatasetThresholds.append(name)
            # remove dictionary entries where none of the LS were bad
            if len(self.badDatasets[name])==0:
                self.badDatasets.pop(name)

    # Use: Checks triggers to make sure none have been bad for to long
    def checkTriggers(self):
        # check what is the latest lumisection for which we have monitoring data
        try:
            #TODO: Use max() instead of sorted()
            latestLS = sorted(list(self.Rates.values())[0].keys())[-1]
        except:
            #TODO: Have a better fallback then just exiting here
            return

        # check L1 rates and raise alarms
        live_l1_rate = self.parser.getL1APhysics(self.runNumber, self.lastLS, self.currentLS)
        dead_l1_rate = self.parser.getL1APhysicsLost(self.runNumber, self.lastLS, self.currentLS)
        rates = {}
        try:
            rates['total'] = live_l1_rate[latestLS] + dead_l1_rate[latestLS]
        except:
            rates['total'] = 0.
        for trigger in self.Rates:
            try:
                rates[trigger] = self.Rates[trigger][latestLS][0]
            except:
                rates[trigger] = 0.
        #if self.LHCStatus[0] == "Stable" and self.LHCStatus[1] >= 3 and self.isUpdating:
        if self.sendAudioAlerts and self.LHCStatus[0] == "Stable" and self.LHCStatus[1] >= 3 and self.isUpdating:
            if not self.l1t_rate_alert.check(rates):
                #pass
                self.l1t_rate_alert.alert()

    # Use: Prints warnings and sends mail
    def runMail(self):
        # Print warnings for triggers that have been repeatedly misbehaving
        for trigger in self.badRates:
            if self.badRates[trigger][1]:
                if self.badRates[trigger][0] >= 1:
                    print("Trigger %s has been out of line for more than %.1f minutes" % (trigger, float(self.badRates[trigger][0])*self.scale_sleeptime))
                # We want to send an alert to mattermost whenever a trigger exits the acceptable threshold envelope
                inlist = 0
                for sublist in range(len(self.mattermostTriggers)):
                    if trigger == self.mattermostTriggers[sublist][0]:
                        inlist = 1
                        break
                if inlist == 0 and self.badRates[trigger][0] == self.maxCBR:
                    if self.badRates[trigger][6]:
                        if self.LHCStatus[0] == "Stable":
                            self.mattermostTriggers.append( [ trigger, self.badRates[trigger][2], self.badRates[trigger][3], self.badRates[trigger][4], self.badRates[trigger][5] ] )
                    else:
                        self.mattermostTriggers.append( [ trigger, self.badRates[trigger][2], self.badRates[trigger][3], self.badRates[trigger][4], self.badRates[trigger][5] ] )

        # if any streams or datasets are bad, send mattermost alert
        # if triggers are bad for longer than the chosen mattermostPeriod, send mattermost alert
        if ((len(self.badStreams) > 0 and self.isUpdating) 
                or (len(self.badDatasets) > 0 and self.isUpdating) 
                or (len(self.mattermostTriggers) > 0 and self.isUpdating and ((time.time() - self.mattermostSendTime) > self.mattermostPeriod))
           ):
            self.sendMail(self.mattermostTriggers, self.badStreams, self.badDatasets)
            
            # if a trigger alert has been sent, reset time and reset mattermost triggers list
            if len(self.mattermostTriggers) > 0 and self.isUpdating and ((time.time() - self.mattermostSendTime) > self.mattermostPeriod):
                self.mattermostSendTime = time.time()
                self.mattermostTriggersSum += len(self.mattermostTriggers)
                self.mattermostTriggers = []

            self.badStreams = {}
            self.badDatasets = {}

    # Use: Sleeps and prints out waiting dots
    def sleepWait(self):
        if not self.quiet:
            if self.simulate:
                print("Sleeping for %.1f sec before next query" % (60.0*self.scale_sleeptime_simulate))
            else:
                print("Sleeping for %.1f sec before next query" % (60.0*self.scale_sleeptime))

        for iSleep in range(20):
            if not self.quiet: write(".")
            sys.stdout.flush()
            if self.simulate:
                time.sleep(3.0*self.scale_sleeptime_simulate)
            else:
                time.sleep(3.0*self.scale_sleeptime)
        sys.stdout.flush()
        print("")

    # Use: Loads the fit data from the fit file
    # Parameters:
    # -- fitFile: The file that the fit data is stored in (a pickle file)
    # Returns: The input fit data
    def loadFit(self, fileName):
        if fileName == "":
            return None
        InputFit = {} # Initialize InputFit (as an empty dictionary)
        # Try to open the file containing the fit info
        try:
            pkl_file = open(fileName, 'rb')
            InputFit = pickle.load(pkl_file)
            pkl_file.close()
        except:
            # File failed to open
            print("Error: could not open fit file: %s" % (fileName))
        # Re format the fits file
        if 'triggers' in InputFit:
            #InputFit = InputFit['triggers']
            FormattedFit = {}
            for trg in InputFit['triggers']:
                FormattedFit[trg] = InputFit['triggers'][trg]['user_input']
            return FormattedFit
        else:
            return InputFit

    # Use: Calculates the expected rate for a trigger at a given ilumi based on our input fit
    def calculateRate(self, triggerName, ilum):
        # Return single numerical value for cosmic ref. rates
        if self.run_type == 'cosmics':
            InputFit = self.loadFit('Fits/cosmics/referenceFits_cosmics_monitored.pkl')
            return InputFit[triggerName]
        # Make sure we have a fit for the trigger
        paramlist = []
        if not self.InputFitHLT is None and triggerName in self.InputFitHLT:
            paramlist = self.InputFitHLT[triggerName]
        elif not self.InputFitL1 is None and triggerName in self.InputFitL1:
            paramlist = self.InputFitL1[triggerName]
        else:
            return 0
        # Calculate the rate
        if paramlist[0] == "exp":          # Exponential
             funcStr = "%.15f + %.5f*exp( %.15f+%.15f*x )" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4])
        elif paramlist[0] == "linear":     # Linear
            funcStr = "%.15f + x*%.15f" % (paramlist[1], paramlist[2])
        elif paramlist[0] == "sinh":
            funcStr = "%.15f + %.15f*sinh(%.15f*x)" % (paramlist[3], paramlist[2], paramlist[1])
        else:                               # Polynomial
            funcStr = "%.15f+x*(%.15f+ x*(%.15f+x*%.15f))" % (paramlist[1], paramlist[2], paramlist[3], paramlist[4])

        fitFunc = ROOT.TF1("Fit_"+triggerName, funcStr)
        if self.pileUp:
            if self.numBunches[0] > 0:
                return self.numBunches[0]*fitFunc.Eval(ilum/self.numBunches[0]*ppInelXsec/orbitsPerSec)
            else:
                return 0
        return fitFunc.Eval(ilum)

    # Use: Gets the MSE of the fit
    def getMSE(self, triggerName):
        paramlist = []
        if not self.InputFitHLT is None and triggerName in self.InputFitHLT:
            paramlist = self.InputFitHLT[triggerName]
        elif not self.InputFitL1 is None and triggerName in self.InputFitL1:
            paramlist = self.InputFitL1[triggerName]
        else:
            return 0
        if self.pileUp:
            return self.numBunches[0]*paramlist[5]
        return paramlist[5] # The MSE
    
    # Use: create text for mattermost alerts for bad streams
    # Return: text for stream alert
    def streamAlerts(self, badStreams):
        # Stream alert title
        text = "Streams exceeding threshold: \n"
        text += "| Stream | LS | Max Rate (Hz) | Alert Threshold (Hz) | Critical Alert Threshold (Hz) |\n"
        text += "| --- | --- | --- | --- | --- | \n"

        # loop through bad streams, creates one row for each bad stream and summarizes the LS currently queried 
        for name in badStreams.keys():
            LS = []
            streamRates = []
            for item in badStreams[name]:
                LS.append(item[0])
                streamRates.append(item[1])

            text += f"| {name} | {str(LS)[1:-1]} | "
            try: 
                text += f"{max(streamRates):.2f} | "
            except: 
                text += f"{str(streamRates)} | "
            
            try: 
                text += f" {self.streamThresholds[name][1]} | {self.streamThresholds[name][0]} |\n"
            except: 
                text += f" |  | \n"
        
        return text

    # Use: create text for mattermost alerts for bad datasets
    # Return: text for dataset alert
    def datasetAlerts(self, badDatasets):
        # Dataset alert title
        text = "Datasets exceeding threshold: \n"
        text += "| Dataset | LS | Max Rate (Hz) | Alert Threshold (Hz) | Critical Alert Threshold (Hz) | \n"
        text += "| --- | --- | --- | --- | --- | \n"

        # loop through bad datasets, creates one row for each bad dataset and summarizes the LS currently queried
        for name in badDatasets.keys():
            LS = []
            datasetRates = []
            for item in badDatasets[name]:
                LS.append(item[0])
                datasetRates.append(item[1])

            text += f"| {name} | {str(LS)[1:-1]} | " 
            try: 
                text += f" {max(datasetRates):.2f} | " 
            except: 
                text += f" {str(datasetRates)} | "
                        
            try: 
                text += f" {self.datasetThresholds[name][1]} | {self.datasetThresholds[name][0]} | \n"
            except: 
                text += f" |  | \n"

        return text

    # Use: create text for mattermost alerts for bad triggers
    # Return: text for trigger alert
    def triggerAlerts(self, messageTriggers):  
        text = "Trigger rates deviating from acceptable and/or expected values: \n\n"
        text += "| Path | Actual | Expected | Unprescaled Expected/nBunches | Unprescaled Actual/nBunches | Deviation |\n"
        text += "| --- | --- | --- | --- | --- | --- |\n"

        for triggerName, rate, expected, dev, ps in messageTriggers:
            if dev is None:
                dev = -999
            if self.numBunches[0] == 0:
                text += f"| {stringSegment(triggerName, 35)} | {rate} Hz |\n"
            else:
                if expected > 0:
                    try: 
                        tmp_str = ""
                        tmp_str += f"| {stringSegment(triggerName, 35)} | {rate:.1f} Hz |"
                        tmp_str += f"{expected:.1f} Hz | " 
                        tmp_str += f"{expected*ps/self.numBunches[0]:.5f} Hz |"
                        tmp_str += f"{rate*ps/self.numBunches[0]:.5f} Hz |" 
                        tmp_str += f"{dev:.1f} | \n"
                        text += tmp_str
                    except: 
                        tmp_str = ""
                        tmp_str += f"| {stringSegment(triggerName, 35)} | {str(rate)} Hz |"
                        tmp_str += f"{str(expected)} Hz | " 
                        tmp_str += f"{str(expected*ps/self.numBunches[0])} Hz |"
                        tmp_str += f"{str(rate*ps/self.numBunches[0])} Hz |" 
                        tmp_str += f"{str(dev)} | \n"
                        text += tmp_str
                else:
                    try: 
                        text += f"| {stringSegment(triggerName, 35)} | {rate:.1f} Hz |\n"
                    except:
                        text += f"| {stringSegment(triggerName, 35)} | {str(rate)} Hz |\n"
        return text
    
    # Use: Sends an email alert
    # Parameters:
    # -- mailTriggers: A list of triggers that we should include in the mail, ( { triggerName, aveRate, expected rate, standard dev } )
    # Returns: (void)
    def sendMail(self,messageTriggers, badStreams, badDatasets):        
        text = "| Run | Lumisections | Average inst. lumi | Average PU | Trigger Mode | Prescale Column |\n"
        text += "| --- | --- | --- | --- | --- | --- | \n"
        text += f"| {self.runNumber} | {self.lastLS} - {self.currentLS} | " 
        
        try: 
            text += f" {self.lumi_ave:.0f} x 10^30 cm-2 s-1 |"
        except: 
            text += f" {str(self.lumi_ave)} x 10^30 cm-2 s-1 |"
        
        try: 
            text += f" {self.pu_ave:.2f} |"
        except: 
            text += f" {str(self.pu_ave)} |"
        
        text += f" {self.triggerMode} | {str(self.lumiData[-1][2])} | \n\n"

        # Print alerts if the query fails or if any of the streams/dataset don't have provided thresholds from the query
        if self.query_error == True: 
            text += "Warning: Authentication and/or query of hltsupervisor failed, stream and dataset thresholds not udpated. \n\n"
            self.query_error = False

        # if len(self.missingStreamThresholds) > 0: 
        #     text += "Warning: The following streams are missing thresholds: \n"
        #     text += f"{str(self.missingStreamThresholds)[1:-1]} \n\n "

        # if len(self.missingDatasetThresholds) > 0: 
        #     text += "Warning: The following datasets are missing thresholds: \n"
        #     text += f"{str(self.missingDatasetThresholds)} \n\n "

        # If there are streams or datasets above their threshold, send an alert
        if len(badStreams) > 0:
            text += self.streamAlerts(badStreams)
            text += '\n'
        if len(badDatasets) > 0: 
            text += self.datasetAlerts(badDatasets)
            text += '\n'
        if len(self.mattermostTriggers) > 0 and self.isUpdating and ((time.time() - self.mattermostSendTime) > self.mattermostPeriod): 
            text += self.triggerAlerts(messageTriggers)

        header = 'MATTERMOST MESSAGES DISABLED'
        if self.sendMattermostAlerts_static and self.sendMattermostAlerts_dynamic:
            header = ' SENDING MESSAGE TO MATTERMOST '
            mattermostAlert(text)
        print("\n{header:{fill}^{width}}\n{body}\n{footer:{fill}^{width}}".format(header=header,footer='',body=text,width=len(header)+6,fill='-'))

    # Use: save variables at the end of run to send run report
    # Return: (void), updates relevant variables
    def saveRunInfo(self):
        self.saveRunNumber = self.runNumber
        self.saveLS = self.currentLS
        self.saveTriggerMode = self.triggerMode
        self.saveLumi_ave = self.runLumi_ave
        self.savePu_ave = self.runPu_ave
        self.saveLumiData = self.lumiData

    # Use: Send summary report to mattermost, and print out the same report on CLI
    def sendReport(self):

        text = "Run Report: \n\n"
        text += "| Run | Last Lumisection | Average inst. lumi | Average PU  | Trigger Mode | No. Trigger Alerts | Last Used Prescale Column | \n"
        text += "| --- | --- | --- | --- | --- | --- | --- | \n"
        text += f"| {self.saveRunNumber} | {self.saveLS} |"

        try:
            text += f"{self.saveLumi_ave:.0f} x 10^30 cm-2 s-1 |"
        except:
            text += f"{str(self.saveLumi_ave)} 10^30 cm-2 s-1 |"

        try:
            text += f"{self.savePu_ave:.2f} |" 
        except:
            text += f"{str(self.savePu_ave)} |" 

        text += f"{str(self.saveTriggerMode)} |" 
        text += f"{str(self.mattermostTriggersSum)} |"

        text += str(self.saveLumiData[-1][2])+ " |\n\n "

        header = 'MATTERMOST MESSAGES DISABLED'
        if self.sendMattermostAlerts_static and self.sendMattermostAlerts_dynamic:
            header = ' SENDING MESSAGE TO MATTERMOST '
            mattermostAlert(text)
            print("SENDING MESSAGE TO MATTERMOST")
            print("Mattermost Summary report")
            print(text)

    # Use: Dumps trigger thresholds to a JSON file
    # Returns: (void)
    def dumpTriggerThresholds(self,triggers,ilum,fp_name):
        # Format: {'trigger_name': [central_value,one_sigma_variance]}
        thresholds = {}
        for t in triggers:
            rate = self.calculateRate(t,ilum)
            mse = self.getMSE(t)
            if rate == 0 or mse == 0:
                # Skip triggers which are missing fits
                continue
            thresholds[t] = [rate,mse]
        with open(fp_name,'w') as fp:
            json.dump(thresholds,fp,indent=4,separators=(',',': '),sort_keys=True)

    # Checks the config file and updates options accordingly
    def updateOptions(self):
        if self.lastCfgFileAccess < os.stat(self.configFilePath).st_mtime:
            self.lastCfgFileAccess = os.stat(self.configFilePath).st_mtime
            print('\nConfiguration file has been modified (or this is the first query), reading file...')
            configFile = open(self.configFilePath)
            #old_properties = copy.deepcopy(self.__dict__)
            old_properties = {}
            for k,v in self.__dict__.items():
                if k not in self.PROTECTED:
                    old_properties[k] = copy.deepcopy(v)
            try:
                properties_dict = json.load(configFile)
                #print '\tDev thresholds prior to updating:' , self.trgDevThresholds
                self.setProperties(**properties_dict)
                #print '\tDev thresholds after updating:' , self.trgDevThresholds
                #new_properties = copy.deepcopy(self.__dict__)
                new_properties = {}
                for k,v in self.__dict__.items():
                    if k not in self.PROTECTED:
                        new_properties[k] = copy.deepcopy(v)
                prop_changed = False
                for prop in list(new_properties.keys()):
                    #if new_properties[prop] != old_properties[prop] and (str(new_properties[prop]).find('<') == -1):
                    if (new_properties[prop] != old_properties[prop]) and not (prop in self.PROTECTED):
                        print("   ",prop,"has been changed from",old_properties[prop],"to",new_properties[prop])
                        prop_changed = True
                if prop_changed == False:
                    print('    No values of properties changed')
            except:
                print('[ERROR] Error loading configuration file, properties not updated. Please check configuration file for syntax errors.')
                self.lastCfgFileAccess = 0 # Set last access to 0 so that we keep trying to load the file (and printing the error) till the issue is resolved
            configFile.close()
            self.optionsCheck() # Check that the specified options don't conflict
        #else:
            #print '\nNo updates to confiuration file'

    # Checks that the specified options do not conflict
    def optionsCheck(self):
        if self.simulate:
            if self.sendMattermostAlerts_static==True or self.sendMattermostAlerts_dynamic==True or self.sendAudioAlerts==True:
                self.sendMattermostAlerts_static = False
                self.sendMattermostAlerts_dynamic = False
                self.sendAudioAlerts = False
                print("\n[WARNING] Alerts should not be on in simulate mode, turning off alerts\n")
                #self.printProperties()

    # Checks for non-default trigger thresholds and sets thresholds accordingly
    def findTrgThreshold(self,trigger):
        if self.usePerDiff:
            if trigger in self.trgPerDiffThresholds:
                trgPercAccept = self.trgPerDiffThresholds[trigger]
            else:
                trgPercAccept = self.percAcceptDefault # Set to default value
            return trgPercAccept
        else:
            if trigger in self.trgDevThresholds:
                trgDevAccept = self.trgDevThresholds[trigger]
            else:
                trgDevAccept = self.devAcceptDefault # Set to default value
            return trgDevAccept

    # Checks if a given property exists
    def hasProperty(self,k):
        ret = k in self.__dict__
        if not ret:
             print("    [ERROR] Unknown property: %s" % (k))
        return ret

    # Sets a property to specified value
    def setProperties(self,**kwargs):
        for k,v in kwargs.items():
            if k in self.PROTECTED:
                print("    [ERROR] Skipping protected property: %s" % (k))
                continue
            elif not self.hasProperty(k):
                continue
            if isinstance(v, list):
                self.__dict__[k] = [x for x in v]
            elif isinstance(v,dict):
                self.__dict__[k] = {}
                for k2,v2 in v.items():
                    self.__dict__[k][k2] = v2
            else:
                self.__dict__[k] = v

    # Prints all properties (by catagory)
    def printProperties(self):
        numb_dict = {'Protected':{},'NotProtected':{}}
        string_dict = {'Protected':{},'NotProtected':{}}
        dict_dict = {'Protected':{},'NotProtected':{}}
        list_dict = {'Protected':{},'NotProtected':{}}
        other_dict = {'Protected':{},'NotProtected':{}}
        for k,v in self.__dict__.items():
            #print "%s:" % (k),v
            if type(v) == int or type(v) == float or type(v) == bool:
                if k in self.PROTECTED: numb_dict['Protected'][k] = v
                else: numb_dict['NotProtected'][k] = v
            elif type(v) == str:
                if k in self.PROTECTED: string_dict['Protected'][k] = v
                else: string_dict['NotProtected'][k] = v
            elif type(v) == dict:
                if k in self.PROTECTED: dict_dict['Protected'][k] = v
                else: dict_dict['NotProtected'][k] = v
            elif type(v) == list:
                if k in self.PROTECTED: list_dict['Protected'][k] = v
                else: list_dict['NotProtected'][k] = v
            else:
                if k in self.PROTECTED: other_dict['Protected'][k] = v
                else: other_dict['NotProtected'][k] = v
        print(' ')
        print('------------------------------------------')
        print("\nPrinting all properties (grouped by type):\n")
        print('Numbers and booleans:')
        for k,v in numb_dict['Protected'].items():
            print('    PROTECTED ',k,': ', v)
        for k,v in numb_dict['NotProtected'].items():
            print('   ',k,':',v)
        print(' ')
        print('Strings:')
        for k,v in string_dict['Protected'].items():
            print('    PROTECTED ',k,': ', v)
        for k,v in string_dict['NotProtected'].items():
            print('   ',k,':',v)
        print(' ')
        print('Dictionaries:')
        for k,v in dict_dict['Protected'].items():
            print('    PROTECTED ',k)  #,': ', v # Just print keys, values take up too much space
        for k,v in dict_dict['NotProtected'].items():
            print('   ',k) #,':',v
        print(' ')
        print('Lists:')
        for k,v in list_dict['Protected'].items():
            print('    PROTECTED ',k) #,': ', v
        for k,v in list_dict['NotProtected'].items():
            print('   ',k) #,':',v
        print(' ')
        print('Other types:')
        for k,v in other_dict['Protected'].items():
            print('    PROTECTED ',k,': ', v)
        for k,v in other_dict['NotProtected'].items():
            print('   ',k,':',v)
        print(' ')
        print('------------------------------------------')
        print(' ')

## ----------- End of class ShiftMonitor ------------ ##

