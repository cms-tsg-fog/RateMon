import requests
import json
import yaml

stream = open(str('mattermostHook.yaml'), 'r')
cfg  = yaml.safe_load(stream)
hook = cfg['mattermost_hook']

text = 'sending mattermost alert'
url = f"https://mattermost.web.cern.ch/hooks/{hook}"
r = requests.post(url,data=json.dumps({"text" : text}))

#payload={"text": "Hello, this is some text\nThis is more text. :tada:"}

#POST /hooks/{hook} HTTP/1.1
#Host: marttermost.web.cern.ch
#Content-Type: application/json
#Content-Length: 63

#{"text": "Hello, this is some text\nThis is more text. :tada:"}
