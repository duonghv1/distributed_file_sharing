import hashlib
import os

class File:
    def __init__(self, file_path):
        self.file_name = file_path.split('/')[-1]
        self.hash = hash_256(file_path)
        self.file_size = os.path.getsize(file_path)

    def to_dict(self):
        return self.__dict__


class FileStore:
    def __init__(self, base_directory):
        self.base_directory = base_directory
        self.files = []
        self.load_files()

    def get_files(self):
        return self.files

    def load_files(self):
        files = []
        for f in os.listdir(self.base_directory):
            file_path = os.path.join(self.base_directory, f)
            if os.path.isfile(file_path):
                files.append(File(file_path).to_dict())
        self.files = files


def hash_256(file_path):
    """Takes the file path and returns the hash of the file using SHA256"""
    hash256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash256.update(chunk)
    return hash256.hexdigest()
