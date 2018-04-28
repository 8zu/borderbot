from collections import namedtuple
import getpass
import json

import requests as req

from result import *

Credential = namedtuple('Credential', ['username', 'password'])

class HttpException(object):
    def __init__(self, status_code, reason):
        self.status_code = status_code
        self.reason = reason

    def __str__(self):
        return f'ERROR [{self.status_code}]: {self.reason}'

class APIEndpoint(object):
    def __init__(self, endpoint, cred={}):
        self.cred = cred
        self.endpoint = endpoint

    def __getattr__(self, part):
        return APIEndpoint(self.endpoint + "/" + part, cred=self.cred)

    def __getitem__(self, part):
        return APIEndpoint(self.endpoint + "/" + part, cred=self.cred)

    def __str__(self):
        return f"<APIEndpoint \"{self.endpoint}\">"

    __repr__ = __str__

    def get(self, **params):
        res = req.get(self.endpoint, auth=tuple(self.cred), params=params)
        if res.ok:
            return Ok(res.text)
        else:
            return Err(HttpException(res.status_code, res.reason))

    def get_json(self, **params):
        try:
            return self.get(**params).map(json.loads)
        except json.JSONDecodeError as json_err:
            return Err(json_err)

    def put(self, payload):
        raise NotImplementedError()

    def post(self, payload):
        raise NotImplementedError()

    def delete(self, payload):
        raise NotImplementedError()

def get_cred():
    return Credential(username=getpass.getuser(), password=getpass.getpass())
