import aiohttp
import asyncio
import aiofiles
import os
import time
import hashlib
from aioconsole import aprint
from .file_store import File, Chunk

MAX_ATTEMPTS = 3

class FileDownloader:
    def __init__(self, base_directory, file_data, chunks):
        self.base_directory = base_directory
        self.file_data = file_data
        self.chunks = chunks
        self.file_path = self.base_directory + '/' + self.file_data['file_name']
        self.temp_file_path = self.file_path + '.download'
        self.file_lock = asyncio.Lock()

    def init_file(self):
        file_size = self.file_data['file_size']
        with open(self.temp_file_path, 'wb') as file:
            file.truncate(file_size)

    async def download_piece(self, session, chunk, start, end, peers):
        failed_peers = set()
        while not peers.empty():
            peer = await peers.get()
            url = f"http://{peer}/chunks/{chunk.chunk_hash}"
            headers = {"Range": f"bytes={start}-{end}"}
            attempt = 0
            while attempt < MAX_ATTEMPTS:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 206:
                            return await response.read(), failed_peers
                        else:
                            raise Exception
                except Exception as e:
                    failed_peers.add(peer)
                    attempt += 1
                    asyncio.sleep(0.5)
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 206:
                        return await response.read(), failed_peers
                    else:
                        raise Exception
            except Exception as e:
                failed_peers.add(peer)
        return None, failed_peers

    async def download_chunk(self, session, chunk):
        num_peers = len(chunk.peers)
        piece_size = chunk.size // num_peers
        download_coroutines = []
        for i, peer in enumerate(chunk.peers):
            start = chunk.offset + i * piece_size
            end = start + piece_size - 1 if i < num_peers - 1 else chunk.offset + chunk.size - 1
            peers = asyncio.Queue()
            [await peers.put(chunk.peers[(i + j) % num_peers]) for j in range(num_peers)]
            download_coroutines.append(self.download_piece(session, chunk, start, end, peers))
        result = await asyncio.gather(*download_coroutines, return_exceptions=True)
        all_failed_peers = set()
        chunk_data = b''
        for piece, failed_peers in result:
            all_failed_peers.update(failed_peers)
            if piece:
                chunk_data += piece
        chunk_hash = hashlib.sha256(chunk_data).hexdigest()
        if chunk_hash == chunk.chunk_hash.split(":")[1]:
            await aprint(f"Downloaded chunk: {chunk.chunk_hash}")
        else:
            await aprint(f"Failed to download chunk: {chunk.chunk_hash}")
        async with self.file_lock:
            await self.write_chunk_to_file(chunk.offset, chunk_data)
        return chunk.chunk_hash, all_failed_peers

    async def write_chunk_to_file(self, offset, data):
        async with aiofiles.open(self.temp_file_path, 'rb+') as file:
            await file.seek(offset)
            await file.write(data)
            await file.flush()

    async def download_file(self):
        start_time = time.time()
        self.init_file()
        failed_peers = []
        try:
            async with aiohttp.ClientSession(trust_env=True) as session:
                download_coroutines = []
                for chunk_data in self.chunks:
                    chunk = Chunk(**chunk_data)
                    download_coroutines.append(self.download_chunk(session, chunk))
                results = await asyncio.gather(*download_coroutines)
                for item in results:
                    failed_peers.append(item)
                file = File(self.temp_file_path, self.file_data['file_name'], self.file_data['chunk_size'])
                if file.hash() == self.file_data['file_hash']:
                    os.rename(self.temp_file_path, self.file_path)
                    await aprint(f"Downloaded file: {self.file_data['file_name']}")
                    await aprint(f"Time elapsed: {time.time() - start_time:.2f} seconds")
                    return True, failed_peers
                else:
                    raise Exception("File hash mismatch. Missing chunks.")
        except Exception as e:
            await aprint(f"Failed to download file: {self.file_data['file_name']}")
            await aprint(f"Error: {e}")
            await aprint("Cleaning up...")
            os.remove(self.temp_file_path)
        return False, failed_peers
