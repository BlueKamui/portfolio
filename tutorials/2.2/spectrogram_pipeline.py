# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "torch",
#   "torchaudio",
#   "matplotlib",
#   "numpy",
# ]
# ///
"""Tutorial part 3: the modality bridge, sound to image and back again.

What this does, in five steps, printing what happened at each one:

  1. Fetches the real Free Spoken Digit Dataset and picks one clip.
  2. Measures how long the clips are, then pads or crops to one common length.
  3. Turns it into a spectrogram: an image of which frequencies are present when.
  4. Throws the phase away, which is what a plain spectrogram does.
  5. Guesses the phase back with Griffin-Lim and rebuilds a waveform.

Step 2 is yours to decide. `FIXED_LEN` at the top starts at 6,000 samples, which is a guess, and
the step prints what that guess costs against the real spread of clip lengths. Change it, run the
script again, and keep the length you can defend.

What to look for in the output:

  - what your chosen length truncates, and how much silence it pads
  - the spectrogram's two dimensions, frequency bins by time frames, and where each comes from
  - how many phase numbers step 4 discards
  - two error numbers at the end: the picture comes back almost exactly, the waveform does not

Run it from this folder:
    uv run spectrogram_pipeline.py

No `--with` flags: this script lists its own dependencies in the block at the top, and `uv`
reads them. It needs `fsdd.py`, the dataset helper, next to it. The first run downloads the
dataset (about 16 MB) into `.fsdd-cache/` beside this script, and later runs reuse it.

It writes three files: my_roundtrip.png, original.wav and reconstructed.wav. Play both wav
files and compare them by ear.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import torch
import torchaudio
from fsdd import clip_names, fetch_recordings, read_clip, write_wav

HERE = Path(__file__).resolve().parent
CACHE = HERE / ".fsdd-cache"

SR = 8_000          # Samples per second in the dataset's recordings.
FIXED_LEN = 6_000   # The one number this script leaves to you. Step 2 prints the evidence.
N_FFT = 254         # Window width in samples: one spectrogram column is this much audio.
HOP = 63            # How far the window slides between columns, so windows overlap heavily.
N_ITER = 64         # How many guessing rounds Griffin-Lim gets.

# Every file is named <digit>_<speaker>_<number>.wav. Change this to any other file in
# .fsdd-cache/recordings to hear a different digit, or a different speaker saying this one.
CLIP = "3_george_47.wav"


def fix_length(x, length=FIXED_LEN):
    """Cut a clip that is too long, pad a clip that is too short with silence."""
    if x.shape[-1] >= length:
        return x[..., :length]
    return torch.nn.functional.pad(x, (0, length - x.shape[-1]))


def main():
    recordings = fetch_recordings(CACHE)
    print(f"\n=== Step 1: one real clip out of {len(clip_names(recordings))} ===")

    # Reading a clip gives back a pair: the waveform itself, and the digit that was spoken.
    raw, label = read_clip(recordings, CLIP)
    n_raw = raw.shape[-1]
    print(f"Clip {CLIP}: the spoken digit {label}.")
    print(f"A waveform is one number per sample, {SR} samples per second.")
    print(f"This clip is {n_raw} numbers long, so {n_raw / SR:.2f} seconds of sound.")
    first_six = [round(v, 4) for v in raw[:6].tolist()]
    print(f"Its first six numbers: {first_six}")

    print("\n=== Step 2: pad or crop to one common length ===")
    # A generative model needs every example to be the same size, so one length has to cover the
    # whole dataset. Measure the spread first: every clip longer than the length you pick loses
    # its ending, and every clip shorter than it is padded with silence the model has to learn.
    lengths = sorted(len(read_clip(recordings, name)[0]) for name in clip_names(recordings))
    middle = lengths[len(lengths) // 2]
    print(f"Clip lengths: shortest {lengths[0]}, median {middle}, longest {lengths[-1]} samples "
          f"({lengths[0] / SR:.2f} s to {lengths[-1] / SR:.2f} s).")
    print("What a few candidate lengths would cost:")
    for candidate in (2_000, 4_000, 6_000, 8_000, 12_000):
        uncut = sum(length <= candidate for length in lengths) / len(lengths)
        silence = sum(max(candidate - length, 0) for length in lengths) / (candidate * len(lengths))
        print(f"  {candidate:>6} samples ({candidate / SR:.2f} s): {uncut:6.1%} of clips kept "
              f"whole, {silence:5.0%} of every image would be silence")
    fixed = fix_length(raw)
    action = "padding" if n_raw < FIXED_LEN else "cropping"
    print(f"FIXED_LEN is {FIXED_LEN}, so this clip goes from {n_raw} to {FIXED_LEN} samples by "
          f"{action}.")
    print("That number is your decision, not the script's. Change it and run this again.")

    print("\n=== Step 3: turn it into a spectrogram ===")
    # The transform slides a window along the clip and, for each position, measures how much of
    # each frequency is in that window. power=2 asks for energy per frequency, a plain image.
    spec_transform = torchaudio.transforms.Spectrogram(n_fft=N_FFT, hop_length=HOP, power=2)
    spec = spec_transform(fixed.unsqueeze(0))
    n_bins, n_frames = spec.shape[-2], spec.shape[-1]
    print(f"Window: {N_FFT} samples ({N_FFT / SR * 1000:.1f} ms of audio per column).")
    print(f"Hop: {HOP} samples ({HOP / SR * 1000:.1f} ms), so consecutive windows overlap.")
    print(f"Result: {n_bins} frequency bins by {n_frames} time frames.")
    print(f"  {n_bins} bins split 0 to {SR // 2} Hz into steps of {SR / N_FFT:.1f} Hz.")
    print(f"  {n_frames} frames because the window slides along {FIXED_LEN} samples in "
          f"steps of {HOP}.")
    print("That is an image, so audio generation is now the image problem from block 2.1.")

    print("\n=== Step 4: what the spectrogram threw away ===")
    # power=None returns the raw result instead: a complex number per cell, which carries both
    # how much of that frequency there is (magnitude) and where in its cycle it was (phase).
    complex_transform = torchaudio.transforms.Spectrogram(n_fft=N_FFT, hop_length=HOP, power=None)
    complex_spec = complex_transform(fixed.unsqueeze(0))
    magnitude = complex_spec.abs()
    phase = complex_spec.angle()
    n_cells = n_bins * n_frames
    # Proof that the image really is just the magnitudes: squaring them reproduces it exactly.
    check = float((magnitude**2 - spec).abs().max())
    # Pick the loudest cell rather than a fixed one: a cell inside the padded silence has a
    # magnitude near zero, which is a poor example of "how much of this frequency is there".
    loudest = int(magnitude[0].argmax())
    bin_i, frame_i = divmod(loudest, n_frames)
    print(f"The full measurement is {n_bins} x {n_frames} = {n_cells} cells, two numbers each:")
    print(f"  loudest cell (bin {bin_i}, frame {frame_i}): "
          f"magnitude {float(magnitude[0, bin_i, frame_i]):.4f}, "
          f"phase {float(phase[0, bin_i, frame_i]):+.4f} radians")
    print(f"The spectrogram keeps the magnitudes only. Check: squaring them reproduces it, "
          f"largest disagreement {check:.1e}.")
    print(f"So {n_cells} phase numbers were discarded, and the image cannot be played.")

    print("\n=== Step 5: guess the phase back, with Griffin-Lim ===")
    # Griffin-Lim starts from a random phase guess and improves it N_ITER times, keeping the
    # magnitudes fixed, until the result is a waveform whose spectrogram matches the image.
    griffin = torchaudio.transforms.GriffinLim(n_fft=N_FFT, hop_length=HOP, power=2,
                                               n_iter=N_ITER)
    recon = fix_length(griffin(spec)[0])
    print(f"{N_ITER} rounds of guessing, from a random starting phase.")

    # Did the image survive? Re-measure the spectrogram of the rebuilt waveform.
    recon_spec = spec_transform(recon.unsqueeze(0))
    spec_error = float(torch.norm(recon_spec - spec) / torch.norm(spec))
    # Did the waveform survive? Compare the two lists of numbers directly.
    wave_error = float(torch.norm(recon - fixed) / torch.norm(fixed))
    print(f"Spectrogram error: {spec_error:.4f}  (0 = the image came back exactly)")
    print(f"Waveform error:    {wave_error:.4f}  (0 = the sound came back exactly)")
    print("The picture is nearly perfect and the waveform is not, because the phase was a")
    print("guess. Griffin-Lim is also random, so this pair of numbers moves a little each run.")
    print(f"Original waveform, first six numbers:      "
          f"{[round(v, 4) for v in fixed[:6].tolist()]}")
    print(f"Reconstructed waveform, first six numbers: "
          f"{[round(v, 4) for v in recon[:6].tolist()]}")

    # --- Write the three files a student can look at and listen to ---
    fig, axes = plt.subplots(1, 3, figsize=(11, 2.8))
    seconds = torch.arange(FIXED_LEN) / SR

    axes[0].plot(seconds.numpy(), fixed.numpy(), color="#666666", linewidth=0.8)
    axes[0].set_title("1. Waveform in", fontsize=9)
    axes[0].set_xlabel("seconds", fontsize=8)
    axes[0].set_ylabel("amplitude", fontsize=8)

    log_spec = 10 * torch.log10(spec[0] + 1e-10)
    image = axes[1].imshow(log_spec.numpy(), origin="lower", aspect="auto", cmap="cividis",
                           extent=[0, FIXED_LEN / SR, 0, SR / 2])
    axes[1].set_title(f"2. Spectrogram ({n_bins} x {n_frames})", fontsize=9)
    axes[1].set_xlabel("seconds", fontsize=8)
    axes[1].set_ylabel("Hz", fontsize=8)
    fig.colorbar(image, ax=axes[1], label="dB", fraction=0.046, pad=0.04)

    axes[2].plot(seconds.numpy(), recon.numpy(), color="#666666", linewidth=0.8)
    axes[2].set_title("3. Waveform out, after Griffin-Lim", fontsize=9)
    axes[2].set_xlabel("seconds", fontsize=8)
    axes[2].set_ylabel("amplitude", fontsize=8)

    fig.suptitle(f'Digit "{label}", FSDD clip {CLIP}: sound to image and back',
                 fontsize=10, y=1.06)
    fig.tight_layout()
    fig.savefig(HERE / "my_roundtrip.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    write_wav(HERE / "original.wav", fixed, SR)
    write_wav(HERE / "reconstructed.wav", recon, SR)
    print("\nWrote my_roundtrip.png, original.wav and reconstructed.wav.")
    print("Play both wav files. Expect the reconstruction to sound robotic or metallic, even")
    print("though the spectrogram error above is small: that is the guessed phase, audible.")


if __name__ == "__main__":
    main()
