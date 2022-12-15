#import os
#import json
import time
import requests
#import yaml


class APIException(Exception):
    """
    A simple base class to handle makeing the problem dict
    Note it is intended that the derived class actually sets everything 
    """
    def __init__(self,type=None,status=None,title=None,detail=None,instance=None):
        self.type = type
        self.status = status
        self.title = title
        self.detail = detail
        self.instance = instance

    def to_dict(self):
        return {k :v for k,v in vars(self).items() if v is not None}


class OAuthException(APIException):
    def __init__(self,error=None,append_detail=False,instance=None):
        self.status = 500
        self.type = "errors/server_auth"
        self.title = "Server Auth Error"
        self.instance = instance if instance!=None else None
        self.detail = "Server is unable to internally authenticate with CERN Auth service"
        if error!=None:            
            if append_detail:
                self.detail = error
            else:
                self.detail +=f"\nError is:\n{error}"


class OIDCAuth : 
    def __init__(self,client_id,client_secret,audience,auth_url,cert_verify):
        self.client_id = client_id
        self.client_secret = client_secret
        self.audience = audience
        self.auth_url = auth_url
        self.cert_verify = cert_verify
        self.token_time = None
        self.token_json = None
        self.max_token_life = 30

    def auth(self):
        current_time = time.time()
        if self.token_json and self.token_time and current_time - self.token_time < self.max_token_life:
            return

        self.token_time = current_time
        token_req_data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': self.audience
        }
        rep = requests.post(self.auth_url, data=token_req_data, verify=self.cert_verify)
        if rep.status_code!=200:
            raise OAuthException(rep.content.decode())

        self.token_json = rep.json()
        self.token_headers = {'Authorization':'Bearer ' + self.token_json["access_token"], 'content-type':'application/json'}

    def headers(self):
        self.auth()
        return self.token_headers