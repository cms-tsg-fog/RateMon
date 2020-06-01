Generated using
```bash
$ curl -o db2json.json https://cmsoms.cern.ch/agg/api/v1/dbinspector/db2json?filter[table]=ratemon&filter[schema]=cms_trg_l1_mon
$ ../aggregationapi/src/main/resources/python/createEndpointFiles.py --subsystem ratemon --path ratemon --attributes db2json.json --blob bmp x --blob bmp rate --identifying runnumber trigger
```