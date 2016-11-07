#!/bin/bash
# crontab line for this is:
# 59 * * * * lxplus.cern.ch /afs/cern.ch/work/g/gesmith/runCert/RateMon3/RateMon/make_plots_for_cron.sh > /dev/null

thisDir=/afs/cern.ch/work/g/gesmith/runCert/AndrewBranchCron/RateMon
outputDirBase=/afs/cern.ch/user/g/gesmith/www/HLT/RateVsPU/
#outputDirBase=$thisDir/tempTest/ #test

cd $thisDir

theFillsAndRuns=$(python test_dump_fills_runs.py)

theRuns="${theFillsAndRuns[@]:5}"
theFill="${theFillsAndRuns[@]:0:4}"

#theRuns="284006 284014"
#theFill=5450

# Do subset of triggers:
python plotTriggerRates.py --triggerList=monitorlist_COLLISIONS.list --fitFile=Fits/2016/FOG.pkl --saveDirectory=$outputDirBase$theFill $theRuns

# Do "All triggers" plots:
python plotTriggerRates.py --triggerList=monitorlist_ALL.list --fitFile=Fits/AllTriggers/FOG.pkl --saveDirectory=$outputDirBase$theFill/MoreTriggers --cronJob $theRuns


# This is just to grab the run numbers used in the fit:
while read -r line
do
    fitCommand="$line"
done < "Fits/AllTriggers/command_line.txt"

# Adjust the html content in the output dir:
match='<html>'
insertFirst='<h3>Runs used to produce fits:<br>'
#insertSecond=$(echo $fitCommand | sed 's/python plotTriggerRates.py --createFit --nonLinear --triggerList=monitorlist_COLLISIONS.list//')
insertSecond=$(echo $fitCommand | sed 's/python plotTriggerRates.py --createFit --nonLinear --AllTriggers//')
insertThird='</h3>'
insertFourth='<h4><a href="./MoreTriggers/Streams/">Stream Rates</a></h4>'
insertFifth='<h4><a href="./MoreTriggers/Datasets/">Dataset Rates</a></h4>'
insertSixth='<h4><a href="./MoreTriggers/L1_Triggers/">L1 Trigger Rates</a></h4>'

cd $outputDirBase$theFill
appendString=''

for D in `find ./MoreTriggers/ -maxdepth 1 -mindepth 1 -type d | sort`
do
    Dstrip=${D#./MoreTriggers/}
    if [ $Dstrip == 'Monitored_Triggers' ] || [ $Dstrip == 'Streams' ] || [ $Dstrip == 'Datasets' ] || [ $Dstrip == 'L1_Triggers' ]
        then
            continue
    fi
    appendString=$appendString'<h4><a href="'$D'/">'
    appendString=$appendString$Dstrip'</a></h4>\n'
    echo $appendString
done

#insertFourth='<h4><a href="./MoreTriggers/Streams/">Stream Rates</a></h4>'
#insertFifth='<h4><a href="./MoreTriggers/L1_Triggers/">L1 Trigger Rates</a></h4>'
#insertSixth='<h4><a href="./MoreTriggers/PhysicsCommissioning/">HLT Rates (PhysicsCommissioning)</a></h4>'
#insertSeventh='<h4><a href="./MoreTriggers/PhysicsEGamma/">HLT Rates (PhysicsEGamma)</a></h4>'
#insertEighth='<h4><a href="./MoreTriggers/PhysicsMuons/">HLT Rates (PhysicsMuons)</a></h4>'
#insertNineth='<h4><a href="./MoreTriggers/PhysicsHadronsTaus/">HLT Rates (PhysicsHadronsTaus)</a></h4>'
#insertTenth='<h4><a href="./MoreTriggers/PhysicsParkingScoutingMonitor/">HLT Rates (PhysicsParkingScoutingMonitor)</a></h4>'
#insertEleventh='<h4><a href="./MoreTriggers/PhysicsCirculating/">HLT Rates (PhysicsCirculating)</a></h4>'
#insertTwelfth='<h4><a href="./MoreTriggers/PhysicsEndOfFill/">HLT Rates (PhysicsEndOfFill)</a></h4>'

insertThirteenth='<h3>Monitored Triggers:</h3>'
file=$outputDirBase$theFill/index.html

#sed -i "s#$match#$match\n$insertFirst\n$insertSecond$insertThird\n$insertFourth\n$insertFifth\n$insertSixth\n$insertSeventh\n$insertEighth\n$insertNineth\n$insertTenth\n$insertEleventh\n$insertTwelfth\n$insertThirteenth#" $file
sed -i "s#$match#$match\n$insertFirst\n$insertSecond$insertThird\n$insertFourth\n$insertFifth\n$insertSixth\n$appendString$insertThirteenth#" $file
