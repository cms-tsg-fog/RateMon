This generates and compiles an OMS aggregator for the ratemon table.

The db2json.json file was fetched using
```bash
$ curl -o db2json.json https://cmsoms.cern.ch/agg/api/v1/dbinspector/db2json?filter[table]=ratemon&filter[schema]=cms_trg_l1_mon
```