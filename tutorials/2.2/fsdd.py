"""The Free Spoken Digit Dataset: fetching it, and reading a clip out of it.

FSDD is 3,000 recordings of spoken digits, six speakers, 8,000 samples per second, mono, held as
plain WAV files in one GitHub repository: https://github.com/Jakobovski/free-spoken-digit-dataset
(MIT licensed). Every file is named `<digit>_<speaker>_<number>.wav`, so the label is the first
character of the file name.

This module downloads one pinned release as a zip, unpacks the recordings into a cache folder
next to whichever script asked for them, and reads one clip into a tensor. The standard library,
numpy and torch, nothing else: the recordings are 16-bit PCM, which the standard library's `wave`
module reads directly.

There is a wrapper library, `torchfsdd`, that does this in one line. It is not used here because
it cannot be installed: its published `setup.py` declares `torch>=1.8+cpu`, which is not a valid
PEP 440 version specifier, and current setuptools rejects the package before it builds. Thirty
lines of standard library is the cheaper answer, and it also drops the `git` requirement, since
the wrapper fetches the data by cloning the repository.

Import with: from fsdd import fetch_recordings, read_clip, clip_names, write_wav
"""

import io
import shutil
import urllib.request
import wave
import zipfile
from pathlib import Path

import numpy as np
import torch

RELEASE = "v1.0.10"
URL = f"https://github.com/Jakobovski/free-spoken-digit-dataset/archive/refs/tags/{RELEASE}.zip"
SAMPLE_RATE = 8_000
FULL_SCALE = 32_768.0  # 16-bit samples run from -32,768 to 32,767, so this maps them to -1 to 1.


def fetch_recordings(cache_dir):
    """Download the dataset once into `cache_dir`, and return the folder holding the WAV files.

    Later runs find the folder already there and download nothing. The unpacking happens in a
    temporary folder that is renamed at the end, so an interrupted download cannot leave a
    half-filled cache behind that later runs would trust.
    """
    cache_dir = Path(cache_dir)
    recordings = cache_dir / "recordings"
    if recordings.is_dir():
        return recordings

    print(f"Fetching the Free Spoken Digit Dataset {RELEASE}, about 16 MB. This happens once.")
    with urllib.request.urlopen(URL) as response:
        archive = zipfile.ZipFile(io.BytesIO(response.read()))

    partial = cache_dir / "recordings.partial"
    shutil.rmtree(partial, ignore_errors=True)
    partial.mkdir(parents=True)
    for entry in archive.namelist():
        if entry.endswith(".wav") and "/recordings/" in entry:
            (partial / Path(entry).name).write_bytes(archive.read(entry))
    partial.rename(recordings)

    print(f"Unpacked {len(clip_names(recordings))} recordings into {recordings}")
    return recordings


def clip_names(recordings):
    """Every clip in the dataset, sorted, for example 3_george_47.wav."""
    return sorted(path.name for path in Path(recordings).glob("*.wav"))


def read_clip(recordings, name):
    """Read one clip, as (waveform, digit).

    The waveform is a 1-D float tensor running from -1 to 1, one number per sample. The digit is
    the integer the file name starts with.
    """
    path = Path(recordings) / name
    with wave.open(str(path), "rb") as wav:
        if wav.getframerate() != SAMPLE_RATE or wav.getsampwidth() != 2 or wav.getnchannels() != 1:
            raise ValueError(f"{name} is not the 8 kHz 16-bit mono this dataset is meant to be")
        frames = wav.readframes(wav.getnframes())
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32) / FULL_SCALE
    return torch.from_numpy(samples.copy()), int(name.split("_")[0])


def write_wav(path, waveform, sample_rate=SAMPLE_RATE):
    """Write a 1-D float tensor running from -1 to 1 as a 16-bit mono WAV file."""
    samples = np.asarray(waveform.detach().cpu(), dtype=np.float32)
    samples = np.round(np.clip(samples, -1.0, 1.0) * (FULL_SCALE - 1))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(samples.astype("<i2").tobytes())
