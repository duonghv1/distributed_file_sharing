import json
import socket


def serialize(data):
    """Serialize the given data to a JSON string."""
    return json.dumps(data).encode('utf-8')


def deserialize(data):
    """Deserialize the given JSON string"""
    return json.loads(data.decode('utf-8'))


def get_internal_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    return ip

