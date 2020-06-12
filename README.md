# RateMon

Repository with various tools to monitor HLT and L1 rates. More details on the [twiki](https://twiki.cern.ch/twiki/bin/viewauth/CMS/RateMonitoringScriptWithReferenceComparison).

This repository has been [mirrored](https://gitlab.cern.ch/avivace/RateMon) on the CERN gitlab, to allow the usage of the gitlab CI/CD tools. The two are kept in sync.

Each commit triggers a build of a RPM package for the RateMon tools. Those packages are automatically uploaded on [this](https://cernbox.cern.ch/index.php/s/TL7L81EaTE3Z8Zy) public EOS share.


### Preparation

Connect to online (.cms) network or lxplus and install: 

```    
ssh -Y cmsusr.cern.ch
git clone git@github.com:cms-tsg-fog/RateMon.git
cd RateMon
```

### CC7

This is not needed on LXPLUS.

Ratemon now works on CC7 / CentOS.

Prerequisites:

```bash
# Install python
yum install python3
# Install ROOT
yum install root
yum install python36-root
```

Set up a python virtual environment and install python dependencies:

```bash
# Create a virtualenv
python3 -m venv .
# Activate a virtualenv
source bin/activate
# Install RateMon requirements
pip3 install -r requirements.txt
# Set PYTHONPATH to look for ROOT py bindings
export PYTHONPATH="/root/root/lib:/root/lib"
```

### Database configuration

Before running either the plot making script or shift monitor tool, you will need to fill the appropriate database connection info in the `dbConfig.yaml` file.

Then, when running `plotTriggerRates` or `ShiftMonitorTool`, pass the `--dbConfigFile=dbConfig.yaml` argument.

> Note: `dump_l1_prescales`, `findRuns` and `sql_query_tool` scripts still need the database configuration in a "DBConfigFile.py"


### Running

Example:

```bash
python3 plotTriggerRates.py --dbConfigFile=dbConfig.yaml --useFills --createFit --bestFit --triggerList=TriggerLists/monitorlist_COLLISIONS.list 6303
```
