import hashlib
import os
from utils import serialize

DEFAULT_CHUNK_SIZE = 8192
MAX_CHUNKS = 30


class Chunk:
    def __init__(self, chunk_hash, offset, size, peers=None):
        self.chunk_hash = chunk_hash
        self.offset = offset
        self.size = size
        self.peers = peers

    def metadata(self):
        return {
            "chunk_hash": self.chunk_hash,
            "offset": self.offset,
            "size": self.size,
        }


class File:
    """Class to represent a local file and its attributes."""
    def __init__(self, file_path, file_name=None, chunk_size=DEFAULT_CHUNK_SIZE):
        self.file_path = file_path
        self.file_name = file_name if file_name else os.path.basename(file_path)
        self.file_size = os.path.getsize(file_path)
        if self.file_size // chunk_size > MAX_CHUNKS:
            self.chunk_size = self.file_size // MAX_CHUNKS
        else:
            self.chunk_size = chunk_size
        self.chunks = self._chunk_file()

    def metadata(self, serialized=False):
        data = {
            "file_name": self.file_name,
            "file_size": self.file_size,
            "chunk_size": self.chunk_size,
            "chunks": [{**chunk.metadata()} for chunk in self.chunks.values()],
        }
        return serialize(data) if serialized else data

    def hash(self):
        return f"file:{hashlib.sha256(self.metadata(serialized=True)).hexdigest()}"

    def has_chunk(self, chunk_hash):
        return chunk_hash in self.chunks

    def _chunk_file(self):
        """Chunk the file into smaller pieces."""
        chunks = {}
        offset = 0
        with open(self.file_path, "rb") as f:
            while chunk := f.read(self.chunk_size):
                chunk_hash = f"chunk:{hashlib.sha256(chunk).hexdigest()}"
                chunks[chunk_hash] = Chunk(chunk_hash, offset, len(chunk))
                offset += len(chunk)
        return chunks

    def __repr__(self):
        return f'File("{self.file_name}", {self.file_size} bytes, {len(self.chunks)} chunks): {self.hash()}'


class FileStore:
    """Class to read files in a directory and load them into memory."""
    def __init__(self, base_directory, chunk_size=DEFAULT_CHUNK_SIZE):
        self.base_directory = base_directory
        self.chunk_size = chunk_size
        self.files = {}    # Maps file hashes to file objects
        self.file_chunks = {}    # Maps chunk hashes to file hashes

    def get_file(self, hash):
        if hash.startswith('file:'):
            return self.files.get(hash)
        if hash.startswith('chunk:'):
            return self.files.get(self.file_chunks.get(hash))
        return None

    def load_files(self):
        """Load files from local directory. Returns true if new files are found."""
        found_new_files = False
        files = set()
        for f in os.listdir(self.base_directory):
            file_path = os.path.join(self.base_directory, f)
            if os.path.isfile(file_path) and not f.startswith('.') and not f.endswith('.download'):
                file = File(file_path=file_path, chunk_size=self.chunk_size)
                file_hash = file.hash()
                files.add(file_hash)
                if file_hash not in self.files:
                    self.files[file_hash] = file
                    for chunk_hash in file.chunks:
                        self.file_chunks[chunk_hash] = file_hash
                    found_new_files = True
        # Remove files that are no longer present
        previous_files = set(self.files.keys())
        for file_hash in previous_files:
            if file_hash not in files:
                del self.files[file_hash]
        return found_new_files
