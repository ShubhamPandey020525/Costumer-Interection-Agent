import json

def loads(*args, **kwargs):
    return json.loads(*args, **kwargs)

def dumps(*args, **kwargs):
    return json.dumps(*args, **kwargs).encode('utf-8')

JSONDecodeError = json.JSONDecodeError
