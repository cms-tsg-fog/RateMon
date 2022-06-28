# RateMon

Repository with various tools to monitor HLT and L1 rates. More details on the [twiki](https://twiki.cern.ch/twiki/bin/viewauth/CMS/RateMonitoringScriptWithReferenceComparison).

## GitHub & GitLab

This repository is both on Github and [CERN GitLab](https://gitlab.cern.ch/cms-tsg-fog/RateMon), to allow the usage of the gitlab CI/CD tools.
Do any development work on GitLab.

## Development

### Requirements

This code depends on the OMS API client, which can be found [here](https://gitlab.cern.ch/cmsoms/oms-api-client).

To install:
```bash
git clone ssh://git@gitlab.cern.ch:7999/cmsoms/oms-api-client.git
cd oms-api-client
python3 -m pip install -r requirements.txt
python3 setup.py install --user
```

You will also need ROOT and ROOT bindings for Python:
```
yum install python3 root python36-root
```

### Python environment

This project uses a python virtual environment.

To set things up:
```bash
cd ratemon
python3 -m venv .
source bin/activate
pip3 install -r requirements.txt
```

## CI/CD

Each push to GitLab that introduces new commits will start a CI pipeline.
The source for that is the `.gitlab-ci.yml` file.

Each pipeline contains a build of an RPM package for the RateMon tools. These packages are automatically uploaded to [a shared EOS folder](https://cernbox.cern.ch/index.php/s/TL7L81EaTE3Z8Zy).

### Deployment

GitLab CI can deploy to P5. To do this, perform the following steps:

- [Create a new tag](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/tags/new)
- [Create a new pipeline](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/pipelines/new)
  - `Run for` must be set to your newly created tag instead of master
  - Set variables `P5_USER` and `P5_PASS` to your P5 username and password.
- In this newly created pipeline, press the `deploy:P5` play button


### Running plotTriggerRates

```bash
python3 plotTriggerRates.py --useFills --createFit --bestFit --triggerList=TriggerLists/monitorlist_COLLISIONS.list 6303
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
python3 ShiftMonitorTool.py
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

### Run the API server

```bash
python3 app.py
```
