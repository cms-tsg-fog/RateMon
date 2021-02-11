# RateMon

Repository with various tools to monitor HLT and L1 rates. More details on the [twiki](https://twiki.cern.ch/twiki/bin/viewauth/CMS/RateMonitoringScriptWithReferenceComparison).

## GitHub & GitLab

This repository is both on Github and [CERN GitLab](https://gitlab.cern.ch/cms-tsg-fog/RateMon), to allow the usage of the gitlab CI/CD tools.
Do any development work on GitLab.

## Development

Each push to GitLab that introduces new commits will start a CI pipeline.
The source for that is the `.gitlab-ci.yml` file.

Each pipeline contains a build of an RPM package for the RateMon tools. These packages are automatically uploaded to [a shared EOS folder](https://cernbox.cern.ch/index.php/s/TL7L81EaTE3Z8Zy).

### Python environment

This project uses a python virtual environment.
The only exception to this is the root packages, which are supplied via yum.

To set things up:
```bash
yum install python3 root python36-root
cd ratemon
source bin/activate
pip3 install -r requirements.txt
```

## Deployment

GitLab CI can deploy to P5. To do this, perform the following steps:

- [Create a new tag](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/tags/new)
- [Create a new pipeline](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/pipelines/new)
  - `Run for` must be set to your newly created tag instead of master
  - Set variables `P5_USER` and `P5_PASS` to your P5 username and password.
- In this newly created pipeline, press the `deploy:P5` play button

### Database configuration

Before running either the plot making script or shift monitor tool, you will need to fill the appropriate database connection info in the `dbConfig.yaml` file.

Then, when running `plotTriggerRates` or `ShiftMonitorTool`, pass the `--dbConfigFile=dbConfig.yaml` argument.

> Note: `dump_l1_prescales`, `findRuns` and `sql_query_tool` scripts still need the database configuration in a "DBConfigFile.py"


### Running plotTriggerRates

```bash
python3 plotTriggerRates.py --dbConfigFile=dbConfig.yaml --useFills --createFit --bestFit --triggerList=TriggerLists/monitorlist_COLLISIONS.list 6303
```

### Running ShiftMonitorTool

At P5, ratemon is installed for you and available as the `ratemon` Systemd service.

To view logs:
```bash
journalctl -fu ratemon
```

To run outside P5:
```bash
cd ratemon
source venv/bin/activate
python3 ShiftMonitorTool.py --dbConfigFile=dbConfig.yaml
```

### Database Parser

The ShiftMonitorTool has been updated to use the OMS databate parser via the OMS API. 

To switch back to the old database parser run (requires `sudo` access from maintainers):
```bash
sudo systemctl stop ratemon.service
sudo systemctl start ratemon2.service
```

> Note: Other `systemctl` commands are also available, such as: `status`, `restart`, `reload` or `reload-or-restart`.

To view logs:
```bash
journalctl -fu ratemon2
```
