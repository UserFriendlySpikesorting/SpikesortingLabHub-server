#!/usr/bin/env python3
"""Experimental: combine_dat.py with multiprocessing, to see if it is faster on your network.

Needs combine_dat.py in the same folder (it reuses all of its prompts and checks).
Usage is identical:  python combine_dat_mp.py [session_folder] [--workers=4]

How it differs: the output is pre-sized, then worker processes each open the
source and the output themselves and copy one byte range straight to its final
position. Chunks never travel between processes. Output is byte-identical.
"""
import multiprocessing as mp
import os
import sys
import time

import combine_dat

BLOCK = 16 * 1024 * 1024
PIECE = 256 * 1024 * 1024
WORKERS = next((int(a.split("=")[1]) for a in sys.argv if a.startswith("--workers=")), 4)


def copy_range(task):
    src_path, src_off, dst_path, dst_off, length = task
    with open(src_path, "rb") as src, open(dst_path, "r+b") as dst:
        src.seek(src_off)
        dst.seek(dst_off)
        left = length
        while left:
            buf = src.read(min(BLOCK, left))
            if not buf:
                raise IOError(f"unexpected end of {src_path}")
            dst.write(buf)
            left -= len(buf)
    return length


def copy_parallel(files, tmp, total):
    tasks, dst_off = [], 0
    for f in files:
        size = os.path.getsize(f)
        for off in range(0, size, PIECE):
            length = min(PIECE, size - off)
            tasks.append((f, off, tmp, dst_off + off, length))
        dst_off += size

    with open(tmp, "wb") as dst:
        dst.truncate(total)  # pre-size so each worker can write at its own offset

    print(f"{WORKERS} worker processes, {len(tasks)} pieces of up to {PIECE // 2**20} MB")
    done, t0 = 0, time.time()
    with mp.Pool(WORKERS) as pool:
        for n in pool.imap_unordered(copy_range, tasks):
            done += n
            combine_dat.progress(done, total, t0)


if __name__ == "__main__":
    mp.freeze_support()  # needed if this is ever built into a Windows .exe
    combine_dat.main(copy_parallel)
