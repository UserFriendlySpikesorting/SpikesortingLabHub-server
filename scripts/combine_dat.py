#!/usr/bin/env python3
"""Combine Open Ephys continuous.dat files of one session into a single raw .dat.

The session folder is, in order of preference:
  1. a path given on the command line (or a folder dragged onto this file):
       python combine_dat.py "Z:\\...\\2025-05-21_13-39-09"
  2. the current directory, if it is a session folder
  3. the folder this script sits in, if it is a session folder
  4. a path pasted when asked (double-click from anywhere)
Recordings are appended byte-for-byte, in order, no downsampling.
The result is written into the session folder as combined_raw_<session>.dat.

Stdlib only. Run with --dry-run to list what would be combined.
"""
import glob
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor

CHUNK = 64 * 1024 * 1024
PATTERN = os.path.join("Record Node *", "experiment*", "recording*", "continuous", "*", "continuous.dat")


def natural_key(path):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", path)]


def channels(dat):
    """structure.oebin sits in <recording>/, three levels above continuous.dat."""
    stream = os.path.basename(os.path.dirname(dat)) + "/"
    rec = os.path.dirname(os.path.dirname(os.path.dirname(dat)))
    with open(os.path.join(rec, "structure.oebin")) as f:
        for s in json.load(f)["continuous"]:
            if s["folder_name"] == stream:
                return s["num_channels"]
    raise KeyError(f"{stream!r} not found in structure.oebin of {rec}")


def pick_stream(files, root):
    """Group by (record node, stream); never mix different streams into one file."""
    groups = {}
    for f in files:
        rel = os.path.relpath(f, root).split(os.sep)
        groups.setdefault((rel[0], rel[-2]), []).append(f)
    keys = sorted(groups, key=natural_key_pair)
    if len(keys) == 1:
        return groups[keys[0]]
    print("Several streams found:")
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k[0]} / {k[1]}  ({len(groups[k])} recordings)")
    choice = int(input("Combine which one? "))
    return groups[keys[choice - 1]]


def natural_key_pair(k):
    return natural_key(k[0] + "/" + k[1])


def ask_each(files, root):
    """Ask y/n per recording; returns (chosen files, their 1-based positions in the full list)."""
    if len(files) == 1:
        return files, [1]
    print(f"\n{len(files)} recordings found. Answer y/n for each (a = yes to all remaining):")
    chosen, picked, take_all = [], [], False
    for i, f in enumerate(files, 1):
        label = f"{i:>2}. {'/'.join(os.path.relpath(f, root).split(os.sep)[1:3])}  {os.path.getsize(f) / 1e9:6.2f} GB"
        if not take_all:
            while (ans := input(f"{label}  add? [y/n/a] ").strip().lower()) not in ("y", "n", "a"):
                pass
            take_all = ans == "a"
        else:
            print(label + "  add? a")
        if take_all or ans == "y":
            chosen.append(f)
            picked.append(i)
    if not chosen:
        sys.exit("Nothing selected.")
    return chosen, picked


def ranges(nums):
    """[1,2,3,5] -> '1-3,5'"""
    parts, start = [], nums[0]
    for prev, cur in zip(nums, nums[1:] + [None]):
        if cur is None or cur != prev + 1:
            parts.append(str(start) if start == prev else f"{start}-{prev}")
            start = cur
    return ",".join(parts)


def find_session():
    """Session folder: path argument, else this script's folder, else a pasted path."""
    paths = [a for a in sys.argv[1:] if not a.startswith("--")]
    here = os.path.dirname(os.path.abspath(__file__))
    if paths:
        root = paths[0]
    elif glob.glob(os.path.join(os.getcwd(), PATTERN)):
        root = os.getcwd()
    elif glob.glob(os.path.join(here, PATTERN)):
        root = here
    else:
        root = input("Paste the session folder path (e.g. ...\\2025-05-21_13-39-09): ")
    root = os.path.abspath(root.strip().strip('"').strip("'"))
    if not os.path.isdir(root):
        sys.exit(f"Not a folder: {root}")
    return root


def progress(done, total, t0):
    print(f"\r{100 * done / total:5.1f}%  {done / (time.time() - t0) / 1e6:6.0f} MB/s", end="", flush=True)


def copy_threaded(files, tmp, total):
    """Append files into tmp. Double buffering: while this chunk is written, a worker reads the next one."""
    done, t0 = 0, time.time()
    with ThreadPoolExecutor(max_workers=1) as pool, open(tmp, "wb") as dst:
        for f in files:
            with open(f, "rb") as src:
                buf = src.read(CHUNK)
                while buf:
                    next_read = pool.submit(src.read, CHUNK)
                    dst.write(buf)
                    done += len(buf)
                    progress(done, total, t0)
                    buf = next_read.result()


def run(copy=copy_threaded):
    root = find_session()
    session = os.path.basename(root)
    files = sorted(glob.glob(os.path.join(root, PATTERN)), key=natural_key)
    if not files:
        sys.exit(f"No continuous.dat found under {root}\nThis should be the session folder, the one containing 'Record Node ...'.")
    files = pick_stream(files, root)
    total_found = len(files)
    while True:
        chosen, picked = ask_each(files, root)
        gb = sum(os.path.getsize(f) for f in chosen) / 1e9
        if input(f"\nCombine recording(s) {ranges(picked)} ({gb:.2f} GB)? [y/n] ").strip().lower() == "y":
            break
        print("OK, starting over.")
    files = chosen

    suffix = "" if len(files) == total_found else f"_rec{ranges(picked)}"
    out = os.path.join(root, f"combined_raw_{session}{suffix}.dat")
    if os.path.exists(out):
        sys.exit(f"{out} already exists, delete or rename it first.")

    chans = {channels(f) for f in files}
    if len(chans) != 1:
        sys.exit(f"Recordings have different channel counts: {sorted(chans)}")
    n = chans.pop()
    frame = n * 2  # int16

    total = 0
    for f in files:
        size = os.path.getsize(f)
        if size % frame:
            sys.exit(f"{f}\n{size} bytes is not a multiple of {n} channels x 2 bytes")
        print(f"{size / 1e9:7.2f} GB  {os.path.relpath(f, root)}")
        total += size
    print(f"{total / 1e9:7.2f} GB  TOTAL, {n} channels, {total // frame:,} samples")
    print(f"Output: {out}")
    if "--dry-run" in sys.argv:
        return

    tmp = out + ".part"
    try:
        copy(files, tmp, total)
        if os.path.getsize(tmp) != total:
            raise IOError("output size does not match sum of inputs")
        os.replace(tmp, out)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    print("\nDone.")


def main(copy=copy_threaded):
    try:
        run(copy)
    except SystemExit as e:
        if e.code:
            print(e.code)
    except Exception as e:
        print(f"\nERROR: {e}")
    input("\nPress Enter to close...")


if __name__ == "__main__":
    main()
