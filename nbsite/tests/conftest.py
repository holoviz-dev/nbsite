import asyncio
import sys

from contextlib import suppress

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

with suppress(ImportError):
    # If we don't import here it will crash test on macOS in multiprocessing
    # started happening in 7.1+
    import psutil  # noqa: F401
