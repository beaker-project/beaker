
import json
import requests

def json_request(method, url, **kwargs):
    # encode data as json
    data = json.dumps(kwargs.pop('data'))
    # add Content-Type request header
    headers = kwargs.pop('headers', []) + [('Content-Type', 'application/json')]
    # call .request() on the session if given, else the module
    real_request_func = kwargs.pop('session', requests).request
    return real_request_func(method, url, data=data, headers=headers, **kwargs)

def post_json(url, **kwargs):
    return json_request('POST', url, **kwargs)

def put_json(url, **kwargs):
    return json_request('PUT', url, **kwargs)
