#!/usr/bin/env python3

import getopt 
import json
import sys
import socket
import re
from termcolor import colored

sys.argv.pop(0)

cosmics_triggerList = "TriggerLists/monitorlist_COSMICS.list" # default list used when in cosmics mode

from omsapi import OMSAPI

PAGE_LIMIT = 10000

hostname = socket.gethostname()
if "lxplus" in hostname:
    omsapi = OMSAPI("https://cmsoms.cern.ch/agg/api", "v1", cert_verify=False, verbose=False)
    omsapi.auth_krb()
else:
    omsapi = OMSAPI("http://cmsoms.cms:8080/api", verbose=False)

def make_inc_subsys_str(inc_subsys):
    sub_systems = ["TCDS", "TRG", "PIXEL", "TRACKER", "ES", "ECAL", "HCAL", "GEM", "RPC", "DT", "CSC", "L1SCOUT", "DAQ", "DQM", "DCS", "CTPPS", "CTPPS_TOT"]
    subsys_str=""
    for sub_sys in sub_systems:
        colour = 'red'
        if sub_sys in inc_subsys:
            colour = 'green'
        subsys_str += colored(sub_sys,colour)+" "

    return subsys_str

def stripVersion(name):
    if re.match('.*_v[0-9]+',name): name = name[:name.rfind('_')]
    return name

def getSubSystems(runNumber):

    q = omsapi.query("runs")
    q.filter("run_number", runNumber)
    q.per_page = 1
    q.custom("fields", "components")
    try:
        return q.data().json()['data'][0]['attributes']['components']
    except:
        print("Cannot retrieve subsystems")
        return []

def getHLTKey(runNumber):
    
    q = omsapi.query("hltconfig")
    q.set_validation(False)
    q.filter("run_number", runNumber)
    q.per_page = 1
    q.custom("fields", "config_name")
    try:
        return q.data().json()['data'][0]['attributes']['config_name']
    except:
        print("Cannot retrieve HLT Key")
        return ""

def getL1Rates(runNumber):

    L1Rates = {}
    q = omsapi.query("l1algorithmtriggers")
    q.filter("run_number", runNumber)
    q.custom("fields", "name,pre_dt_before_prescale_rate")
    q.per_page = PAGE_LIMIT
    q.custom("group[granularity]", "run")
    try:
        data = q.data().json()['data']
    except:
        print("Failed to get L1 rates")
        return {}
    for item in data:
        L1Rates[item['attributes']['name']] = item['attributes']['pre_dt_before_prescale_rate']
    return L1Rates

def getHLTRates(runNumber):

    HLTRates = {}
    q = omsapi.query("hltpathinfo")
    q.filter("run_number", runNumber)
    q.custom("fields", "path_name,rate")
    q.per_page = PAGE_LIMIT
    try:
        data = q.data().json()['data']
    except:
        print("Failed to get HLT rates")
        return {}
    for item in data:
        HLTRates[stripVersion(item['attributes']['path_name'])] = item['attributes']['rate']
    return HLTRates

def getTotalRates(runNumber):

    q = omsapi.query("runs")
    q.filter("run_number", runNumber)
    q.custom("fields", "l1_rate,hlt_physics_rate")
    q.per_page = 1 
    try:
        data = q.data().json()['data'][0]['attributes']
    except:
        print("Failed to get total rates")
        return {}

    l1_rate =  data['l1_rate']
    hlt_physics_rate = data['hlt_physics_rate']

    totalRates = {'l1_rate':l1_rate, 'hlt_physics_rate':hlt_physics_rate}
    return totalRates

def loadTriggersFromFile(fileName):
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
                TriggerList.append(stripVersion(str(triggerName)))
        except:
            print("Error parsing trigger name in file", fileName)
    return TriggerList

triggerList = loadTriggersFromFile(cosmics_triggerList)

for run in sys.argv:
    HLT_Key = getHLTKey(run)
    sub_systems = getSubSystems(runNumber=run)
    included_subsys = make_inc_subsys_str(sub_systems)
    totalRates = getTotalRates(run)
    l1Rates = getL1Rates(run)
    hltRates = getHLTRates(run)
    
    print("\n------------------------------------------------------------------\n")
    print(run, "    ", HLT_Key, "\n")
    print("Subsystems", included_subsys)
    print("\nL1T Rate:", totalRates['l1_rate'])
    print("HLT Rate (Physics):", totalRates['hlt_physics_rate'],"\n")
    for trig in triggerList:
        if trig[0:4] == "HLT_" and trig in hltRates:
            print("{:35s} {:20f}".format(trig,hltRates[trig]))
        elif trig[0:3] == "L1_" and trig in l1Rates:
            print("{:35s} {:20f}".format(trig,l1Rates[trig]))
