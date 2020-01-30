# Good runs: https://cms-service-dqm.web.cern.ch/cms-service-dqm/CAF/certification/Collisions18/13TeV/ReReco/Cert_314472-325175_13TeV_17SeptEarlyReReco2018ABC_PromptEraD_Collisions18_JSON.txt

goodruns=(305112 315257 315259 315264) 
for i in "${goodruns[@]}"; do 
	python plotTriggerRates.py --dbConfigFile=dbConfig.yaml --triggerList=TriggerLists/monitorlist_COLLISIONS.list "$i";
done