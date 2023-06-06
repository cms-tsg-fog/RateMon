#!/usr/bin/env python3

import os
import sys
import getopt
from MenuAnalyzer import *
from termcolor import colored

def usage():
    print("Usage: "+sys.argv[0]+" <path to cdaq area>")
    print("Options: ")
    print("-v                          Verbose mode (print out ALL checks)")
    print("--doAnalysis=<analysis>     Specify a specific check to so (default: do all)")

def main():
    try:
        opt, args = getopt.getopt(sys.argv[1:],"v",["doAnalysis=","collision","circulating","cosmic"])
    except getopt.GetoptError as err:
        print(str(err))
        usage()
        sys.exit(2)

    if len(args)<1:
        usage()
        sys.exit()

    menu = args[0]
    verbose = False
    toDo = []
    analyzer = MenuAnalyzer(menu)
    useCommandOption = False
    if len(args) == 2: # get options passed on the command line
        useCommandOption = True
        label = args[1]
        if label == "-v":
            Verbose = True
        elif label == "--doAnalysis":
            toDo.append(args)
        elif label == "collision":
            analyzer.requiredContent_collision()
            analyzer.menuMode = 'collision'
        elif label == "circulating":
            analyzer.requiredContent_circulating()
            analyzer.menuMode = 'circulating'
        elif label == "cosmic":
            analyzer.requiredContent_cosmic()
            analyzer.menuMode = 'cosmic'
        else:
            print("\nUnknown option "+label)
            sys.exit()

    if len(toDo)==0: analyzer.AddAllAnalyses()
    else:
        for a in toDo: analyzer.AddAnalysis(a)
    analyzer.Analyze()

    ## check the results
    if not analyzer.expressType=='':
        print("\nEXPRESS Reconstruction will be:  %s" % analyzer.expressType)
    else:
        print("WARNING: Cannot determine express reconstruction")

    print("\n")
    failed=[]
    format = "ANALYSIS%26s  %s"
    pass_txt = colored("SUCCEEDED",'green')
    fail_txt = colored("FAILED",'red')
    for analysis,result in analyzer.Results.items():
        if isinstance(result,list): # list output
            if len(result) == 0:
                print(format % (analysis,pass_txt,))
            else:
                print(format % (analysis,fail_txt,))
                failed.append(analysis)
        else:
            if result==0:
                print(format % (analysis,pass_txt,))
            else:
                print(format % (analysis,fail_txt,))
                failed.append(analysis)

    if len(failed)!=0: print("\nLIST OF FAILED ANALYSES:")
    for analysis in failed:
        print(colored(analyzer.ProblemDescriptions[analysis]+":  ",'red'))
        for line in analyzer.Results[analysis]: print(colored(line,'yellow'))
        print("")
    # Check menu mode
    print("Using menu mode:", analyzer.menuMode)
    if useCommandOption == False and analyzer.useMenuName == False:
        note1_txt = colored("Default collision mode: Menu mode not detected from menu name (usually contains 'physics', 'circulating' or 'cosmic'), and no menu mode specified from command line",'yellow')
        print(note1_txt)
    if useCommandOption == False:
        note2_txt = colored("To manually set a certain menu mode for Event Content check: add to the command line --mode collision / circulating / cosmic",'yellow')
        print(note2_txt)
if __name__=='__main__':
    main()
