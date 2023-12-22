# RateMon

Repository with various tools to monitor HLT and L1 rates. More details on the [training repository](https://gitlab.cern.ch/cms-tsg-fog/training/-/tree/master/).

## GitHub & GitLab

This repository is both on Github and [CERN GitLab](https://gitlab.cern.ch/cms-tsg-fog/RateMon), to allow the usage of the gitlab CI/CD tools.
Do any development work on GitLab.

## Development

### Requirements

This code depends on the OMS API client, which can be found under [cmsoms/oms-api-client](https://gitlab.cern.ch/cmsoms/oms-api-client). It is published on PyPI and has been added as a dependency in `requirements.txt`.

You can run the following commands in an virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

## CI/CD

Each push to GitLab that introduces new commits will start a CI pipeline.
The source for that is the `.gitlab-ci.yml` file.

Each pipeline contains a build of an RPM package for the RateMon tools. These packages are automatically uploaded to [a shared EOS folder](https://cernbox.cern.ch/index.php/s/TL7L81EaTE3Z8Zy).

# Testing and Deploying Changes to RateMon

## Tests to complete before creating a RateMon MR
Before creating a MR, thoroughly test the new code with the following tests. 
All of these tests should be done **after** a `git pull` and a `git checkout` of the new branch has been done on the machine so that the test runs on the new code. 

### Miscellaneous checks
1. Check that in [ShiftMonitorNCR.py](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/blob/master/ratemon/ShiftMonitorNCR.py#L356), `self.sendMattermostAlerts_static` is set to `True`. If this is false, then alerts will not be sent to the RateMon alerts channel on Mattermost. 

### Tests on lxplus
1. Run plotTriggerRates.py: `python3 plotTriggerRates.py --triggerList=TriggerLists/monitorlist_COLLISIONS.list 370725`
2. Run ShiftMonitorTool.py without the config file: `python3 ShiftMonitorTool.py --simulate=370725`
3. Run ShiftMonitorTool.py with the config file: `python3 ShiftMonitorTool.py --simulate=370725 --configFile=ShiftMonitor_config.json`

### Tests on VM (caer)
1. Run plotTriggerRates.py: `python3 plotTriggerRates.py --triggerList=TriggerLists/monitorlist_COLLISIONS.list 370725`
2. Run test queries from the web interface (http://caer.cern.ch/api/v1/ui), with all different combintations of `queryByFill` and `createFit`, while setting the `runNumber` to the corresponding run/fill number for a given `triggerKey`. Preferably, use a recent run/fill and a standard trigger. Make sure the expected output (JSON, ROOT) is produced while monitoring the output on the VM.

### Tests on P5 dev VM (kvm-s3562-1-ip149-08)
**NOTE:** These instructions need to be updated as per [Issue #120](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/issues/120)

Login to machine: 
```
ssh lxplus
ssh cmsusr
ssh kvm-s3562-1-ip149-08
```

This should put you into the directory `/nsfhome0/USERNAME`. 
If it is your first time using the machine, setup the ratemon repository here using `git clone https://gitlab.cern.ch/cms-tsg-fog/ratemon.git`. 

Navigate to the ratemon directory and do a `git pull` and `git checkout` for the branch you want to test. Then run the following two tests: 
1. Test `make_plots_for_cron_manual.py` using a test fill (**This is not available yet. In the meantime manually edit make_plots_for_cron.py to run over a specified fill by commenting out the line `run_lst , fill_num = parser.getRecentRuns()` and replacing it with two lines: `fill_num = 9068` and `run_lst = parser.getFillRuns(fill_num)`**).
2. Test ShiftMonitorTool on the dev machine via a systemctl process: 
```bash
sudo systemctl start ratemon.service
sudo journalctl -fu ratemon
sudo systemctl stop ratemon.service
```

## Deployment

GitLab CI can deploy to P5. To do this, perform the following steps:

- [Create a new tag](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/tags/new)
- [Create a new pipeline](https://gitlab.cern.ch/cms-tsg-fog/ratemon/-/pipelines/new)
  - `Run for` must be set to your newly created tag instead of master
  - Set variables `P5_USER` and `P5_PASS` to your P5 username and password (note that P5 username is the same as CERN username, but P5 password is cmsusr password).
- In this newly created pipeline, press the `deploy:P5` play button
  - In order to manually deploy successfully, you also need to be on the cms ratemon librarian group.

## After Deploying Changes
After deploying changes to the P5 machine, do the following to update the `ater` machine and confirm everything is running as expected. 

1. Check that the P5 machine cron job is running correctly. First, login to the P5 prod machine (`kvm-s3562-1-ip151-84`) and then view the cron job logs with the command `sudo vim /var/spool/mail/hltpro` (with your text editor of choice). The cron job only runs once an hour so this needs to be checked once the cron job for the new RateMon tag is running. 
2. Check the ShiftMonitorTool output logs. On the P5 prod machine, run this command to monitor the logs and confirm there are no errors: `sudo journalctl -fu ratemon`. 
3. Update the `ater` VM. Login to the `ater` machine and connect to the tmux session with `tmux a -t 0`. Then do `CTRL+C` to quit the current server. Next, do a `git pull` and checkout the new tag. Restart the API with `python3 server.py`. Then open https://cmsoms.cern.ch/ratemon/rate_vs_pu/ and click on a rate vs pu plot. If the API is working correctly, there will then be a corresponding interactive "live" plot. 


# Running ShiftMonitorTool

At P5, ratemon is installed for you and available as the `ratemon` Systemd service. This is on the VMs `kvm-s3562-1-ip151-84` (production) and `kvm-s3562-1-ip149-08` (development), which can be accessed from `cmsusr`.

To view logs:
```bash
journalctl -fu ratemon
```

To restart the Systemd service (done if there is an error or after new deployment) it can be done with:

```bash
sudo systemctl stop ratemon.service
sudo systemctl start ratemon.service
```

To run outside P5:
```bash
cd ratemon
source venv/bin/activate
python3 ShiftMonitorTool.py
```

