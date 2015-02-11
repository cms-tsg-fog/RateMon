#!/usr/bin/env python

import sys
from Page1Parser import Page1Parser

WBMPageTemplate = "http://cmswbm/cmsdb/servlet/RunSummary?RUN=%s&DB=cms_omds_lb"

def GetRun(RunNum, fileName, Save, StartLS=999999, EndEndLS=111111):
    print "Getting info for run "+str(RunNum)
    print "This can take several minutes ..."
    
    RunSumPage = WBMPageTemplate % str(RunNum)
    
    Parser = Page1Parser()
    Parser._Parse(RunSumPage)
    [HLTLink,LumiLink,L1Link] = Parser.ParseRunPage()
    
    Parser._Parse(LumiLink)
    Parser.ParseLumiPage(StartLS, EndEndLS)

    if Parser.FirstLS==-1:
        return Parser

    HLTLink = HLTLink.replace("HLTSummary?","HLTSummary?fromLS="+str(Parser.FirstLS)+"&toLS="+str(Parser.LastLS)+"&")
    
    Parser._Parse(HLTLink)
    Parser.ParseRunSummaryPage()

    
    Parser._Parse(L1Link)
    Parser.ParseL1Page()

    L1_LS_Link = L1Link.replace("L1Summary?","L1Summary?fromLS="+str(Parser.FirstLS)+"&toLS="+str(EndEndLS)+"&")
    Parser._Parse(L1_LS_Link)
    Parser.Parse_LS_L1Page()
    
    if Save:
        Parser.Save(fileName)
    print "Done!"

    return Parser
