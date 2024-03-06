import aiohttp.web
import aioconsole
import os
from pyngrok import conf, ngrok


from dotenv import load_dotenv

from file_store import FileStore, File

load_dotenv()


class FileServer:
    def __init__(self, file_store: FileStore, host, port):
        self.file_store = file_store
        self.host = host
        self.port = port
        self.server = aiohttp.web.Application()
        self.create_routes()
        self.rnner = None

    def create_routes(self):
        self.server.router.add_get('', self.handle_root_request)
        self.server.router.add_get('/chunks/{chunk_hash}', self.handle_chunk_request)

    async def handle_root_request(self, request):
        return aiohttp.web.Response(text="Online")

    async def handle_chunk_request(self, request):
        chunk_hash = request.match_info['chunk_hash']
        range_header = request.headers.get('Range')

        file = self.file_store.get_file(chunk_hash)
        if not file:
            return aiohttp.web.Response(status=404, text="Chunk not found")
        if range_header:
            start, end = map(int, range_header.split('=')[1].split('-'))
            return self.serve_content(file, start, end)
        else:
            return aiohttp.web.FileResponse(file.file_path)

    def serve_content(self, file: File, start, end):
        end = min(end, file.file_size)
        length = end - start + 1
        with open(file.file_path, 'rb') as f:
            f.seek(start)
            data = f.read(length)
        headers = {
            'Content-Type': 'application/octet-stream',
            'Content-Range': f'bytes {start}-{end}/{file.file_size}',
            'Content-Length': str(length),
        }
        return aiohttp.web.Response(body=data, status=206, headers=headers)

    async def run(self):
        self.runner = aiohttp.web.AppRunner(self.server)
        await self.runner.setup()
        site = aiohttp.web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        await aioconsole.aprint(f'File Server running on {self.host}:{self.port}')

    async def terminate(self):
        await self.server.shutdown()
        await self.server.cleanup()
        await self.runner.cleanup()





