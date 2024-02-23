import hashlib
import os
from utils import serialize

DEFAULT_CHUNK_SIZE = 8192


class File:
    """Class to represent a local file and its attributes."""
    def __init__(self, file_path, chunk_size):
        self.file_path = file_path
        self.file_name = os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        self.chunk_size = chunk_size
        self.chunk_hashes = self.chunk_file()

    def metadata(self, serialized=False):
        data = {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "chunk_size": self.chunk_size,
            "chunk_hashes": self.chunk_hashes,
        }
        return serialize(data) if serialized else data

    def hash(self):
        return f"file:{hashlib.sha256(self.metadata(serialized=True)).hexdigest()}"

    def chunk_file(self):
        """Chunk the file into smaller pieces."""
        chunks = []
        with open(self.file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                chunks.append(f"chunk:{hashlib.sha256(chunk).hexdigest()}")
        return chunks

    def __repr__(self):
        return f'File("{self.file_name}", {self.file_size} bytes, {len(self.chunk_hashes)} chunks), hash={self.hash()}'


class FileStore:
    """Class to read files in a directory and load them into memory."""
    def __init__(self, base_directory, chunk_size=DEFAULT_CHUNK_SIZE):
        self.base_directory = base_directory
        self.chunk_size = chunk_size
        self.files = {}

    def get_files(self):
        return self.files

    def load_files(self):
        """Load files from local directory. Returns true if new files are found."""
        found_files = False
        for f in os.listdir(self.base_directory):
            file_path = os.path.join(self.base_directory, f)
            if os.path.isfile(file_path) and not f.startswith('.'):
                file = File(file_path, self.chunk_size)
                file_hash = file.hash()
                if file_hash not in self.files:
                    self.files[file.hash()] = file
                    found_files = True
        return found_files
