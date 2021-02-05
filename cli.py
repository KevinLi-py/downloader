import asyncio
import argparse

from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn

from core import Downloader


async def main(url=None, file=None, task_count=None):
    if url is None:
        url = input('url: ')
    if file is None:
        file = input('file: ')
    if task_count is None:
        task_count = int(input('task count (default 10): ').strip() or 10)
    progress = Progress(
        TextColumn('[bold blue]{task.description}', justify='right'),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        "•",
        DownloadColumn(),
        "•",
        TransferSpeedColumn(),
        "•",
        TimeRemainingColumn(),
        refresh_per_second=1
    )
    with open(file, 'wb') as fp, progress:
        async with Downloader(url, fp, {}, task_count) as downloader:
            t_tasks = [progress.add_task('Total', total=downloader.filesize)]
            bytes_last_task = (downloader.filesize -
                               downloader.bytes_per_task * (downloader.task_count - 1))
            for i in range(1, downloader.task_count + 1):
                t_tasks.append(progress.add_task(
                    f'{i}',
                    total=downloader.bytes_per_task
                    if i != downloader.task_count
                    else bytes_last_task
                ))

            def report_hook(task_id, task_downloaded, total_downloaded):
                progress.update(t_tasks[task_id], completed=task_downloaded)
                progress.update(t_tasks[0], completed=total_downloaded)
            await downloader.download(report_hook)
    input('Finished... ')


if __name__ == '__main__':
    parser = argparse.ArgumentParser('Downloader')
    parser.add_argument('--url', '-i', default=None,
                        help='The download url. if not given, read from stdin')
    parser.add_argument('--file', '-o', default=None,
                        help='The output file name. if not given, read from stdin')
    parser.add_argument('--task-count', '-t', default=10, type=int)
    args = parser.parse_args()
    asyncio.run(main(args.url, args.file, args.task_count))
