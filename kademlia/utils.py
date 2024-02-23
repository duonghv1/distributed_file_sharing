import json


def serialize(data):
    """Serialize the given data to a JSON string."""
    return json.dumps(data).encode('utf-8')


def deserialize(data):
    """Deserialize the given JSON string"""
    return json.loads(data.decode('utf-8'))
