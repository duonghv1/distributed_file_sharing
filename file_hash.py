import hashlib


def hash_265(file_path):
    """Takes the file path and returns the hash of the file using SHA256"""
    hash256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash256.update(chunk)
    return hash256.hexdigest()