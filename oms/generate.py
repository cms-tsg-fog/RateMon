#!/usr/bin/env python
## works both in python 2 and 3

import json
import os

c = json.load(open('config.json'))

cmd = "./aggregationapi/src/main/resources/python/createEndpointFiles.py --subsystem {} --path {} --attributes db2json.json --identifying {}".format(c["subsystem"], c["path"], " ".join(c["identifying"]))

for colname, coltype in c["blobs"].items():
  cmd += " --blob {} {}".format(coltype, colname)

print(cmd)
stream = os.popen(cmd)
output = stream.read()
output