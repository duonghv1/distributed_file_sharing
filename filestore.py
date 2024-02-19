import hashlib
import os


class File:
    """Class to represent a local file and its attributes."""
    def __init__(self, file_path):
        name, ext = os.path.splitext(file_path)
        self.file_name = name
        self.filepath = file_path
        self.hash = hash_256(file_path)
        self.file_size = os.path.getsize(file_path)
        self.file_ext = ext

    def to_dict(self):
        return self.__dict__


class FileStore:
    """Class to store files in a directory and load them into memory."""
    def __init__(self, base_directory):
        self.base_directory = base_directory
        self.files = []
        self.hash_to_file = {}
        self.load_files()

    def get_files(self):
        return self.files

    def load_files(self):
        """Load files from local base directory"""
        files = []
        hash_to_file = {}

        for f in os.listdir(self.base_directory):
            file_path = os.path.join(self.base_directory, f)
            if os.path.isfile(file_path) and not f.startswith('.'):
                fileobj = File(file_path)
                files.append(fileobj.to_dict())
                hash_to_file[fileobj.hash] = fileobj
        self.files = files
        self.hash_to_file = hash_to_file


    def find_file_by_hash(self, fhash):
        """Return the file object based on the given hash"""
        if fhash not in self.hash_to_file:
            return None
        
        file = self.hash_to_file[fhash]
        return file


def hash_256(file_path):
    """Takes the file path and returns the hash of the file using SHA256"""
    hash256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hash256.update(chunk)
    return hash256.hexdigest()
