import asyncio
import math
from typing import BinaryIO
import aiohttp

from utils import parse_headers


DEFAULT_HEADERS = parse_headers('''
accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9
sec-ch-ua: "Chromium";v="88", "Google Chrome";v="88", ";Not A Brand";v="99"
sec-ch-ua-mobile: ?0
sec-fetch-dest: document
sec-fetch-mode: navigate
sec-fetch-site: same-origin
sec-fetch-user: ?1
user-agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.146 Safari/537.36
''')


class Downloader:
    def __init__(self, url: str, fp: BinaryIO, headers: dict = DEFAULT_HEADERS, task_count=10) -> None:
        self.session = aiohttp.ClientSession(headers=headers)
        self.url = url
        self.filesize = 0
        self.task_count = task_count
        self.tasks = []
        self.fp = fp
        self.downloaded = 0
        self.bytes_per_task = 0

    async def __aenter__(self):
        await self.session.__aenter__()
        async with await self.session.head(self.url, raise_for_status=True) as res:
            if res.status != 200:
                raise ValueError(
                    f'HTTP Status code must be 200, not {res.status}')
            self.filesize = res.content_length
            if self.filesize is None:
                raise ValueError(f'Content-Length is unknown')
            if 'bytes' not in res.headers['Accept-Ranges']:
                raise ValueError("'bytes' must be in Accept-Ranges")
            self.bytes_per_task = int(
                math.ceil(self.filesize / self.task_count))
            self.fp.truncate(self.filesize)
            return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.__aexit__(exc_type, exc_val, exc_tb)

    async def download(self, report_hook=lambda task_id, task_downloaded, total_downloaded: None):
        self.tasks.clear()

        for i, start in enumerate(range(0, self.filesize, self.bytes_per_task), 1):
            self.tasks.append(asyncio.create_task(
                self.download_range(i, start, report_hook)))
        await asyncio.wait(self.tasks)

    async def download_range(self, i, start, report_hook):
        end = start + self.bytes_per_task - 1
        if end >= self.filesize - 1:
            end = self.filesize - 1
        download_start = start
        while download_start <= end:
            try:
                async with self.session.get(self.url, headers={'Range': f'bytes={download_start}-{end}'}) as res:
                    if res.status != 206:
                        raise ValueError(
                            f'HTTP Status code must be 206, not {res.status}')
                    while True:
                        chunk = await res.content.read(8192)
                        if not chunk:
                            break
                        self.fp.seek(download_start)
                        self.fp.write(chunk)
                        download_start += len(chunk)
                        self.downloaded += len(chunk)
                        report_hook(i, download_start -
                                    start, self.downloaded)
            except ConnectionError:
                pass
