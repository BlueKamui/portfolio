# Subelement 1: comparison design

Decided: Sat 26 September 2026

## The comparison
Two conditions of the same VAE (pythae), trained on MNIST:

- **Condition A:** latent_dim = 2
- **Condition B:** latent_dim = 16

## Why this choice
- Only one thing changes, so any difference in the samples can be traced back to latent size rather than luck or setup.
- On bars and stripes, latent_dim = 2 gave blurry samples (loss ~26) while 16 was sharp but often broke the rule (loss ~14.7). I want to see whether the same trade-off holds on real handwritten digits, where there is no exact "valid image" check.
- My week 2 run (latent_dim = 16, 50 epochs, full 60k) trained in under 2 minutes on my MacBook Air, so both conditions are cheap to run and repeat.

## Held fixed
Same data (full MNIST, 60,000 train / 10,000 test, same order), same 50 epochs, same architecture (pythae default encoder/decoder), same optimiser and learning rate (1e-3), same batch size (64), same BCE reconstruction loss, same seeds for sampling.

## What I will check
- Loss curves for both conditions (first and final loss, train vs eval)
- At least 16 samples per condition, across more than one seed
- The copy check (distance from each sample to its nearest training image), for both
- An honest description of what the samples look like, not what I expected

## Open questions
- Whether a latent walk is worth including as an extra (not as evidence)
- Whether to add a quality number (e.g. torch-fidelity) if visual inspection is not enough
