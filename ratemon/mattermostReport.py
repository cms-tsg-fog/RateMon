import requests
import json
import yaml

def mattermostReport(text):
    try:
        stream = open(str('mattermostHook.yaml'), 'r')
        cfg  = yaml.safe_load(stream)
        hook = cfg['mattermost_hook']
    except:
        print("Unable to get mattermost hook")
        return
    try:
        url = f"https://mattermost.web.cern.ch/hooks/{hook}"
        r = requests.post(url,data=json.dumps({"text" : text}))
    except:
        print("Unable to send message to mattermost")

#payload={"text": "Hello, this is some text\nThis is more text. :tada:"}

#POST /hooks/{hook} HTTP/1.1
#Host: marttermost.web.cern.ch
#Content-Type: application/json
#Content-Length: 63

#{"text": "Hello, this is some text\nThis is more text. :tada:"}
