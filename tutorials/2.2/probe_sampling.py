"""Tutorial part 1a: the sampling probe.

What this does: calls a real, small language model (GPT-2) with the same prompt many times, so
you see the spread sampling actually produces rather than a description of it.

  1. The same prompt twenty times at the same settings, with only the random seed changed.
  2. A temperature sweep: low, default, high.
  3. A top-p sweep: narrow, moderate, off.

What to look for:

  - how many of the twenty completions come out genuinely different from each other
  - which settings make the model repeat itself, and which let it wander
  - one seed across two settings: the completions start the same and split later

Run it from this folder:
    uv run --with transformers --with torch python probe_sampling.py

The first run downloads GPT-2's weights, about 548MB, once. Runs after that are quick on a
laptop CPU.

Then change something and run it again: PROMPT, or one of the values in TEMPERATURES. Both are
right below this line.
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, set_seed

PROMPT = "My favourite thing about weekends is"
N_REPEATS = 20
N_NEW_TOKENS = 12
TEMPERATURES = [0.05, 0.2, 1.0, 1.8, 5.0]  # added 0.05 and 5.0 per the task
TOP_PS = [0.1, 0.9, 1.0]        # 1.0 keeps every token, so it removes nothing


def report(completions):
    """Print one completion per line, then how many of them were different from each other."""
    for seed, text in enumerate(completions):
        print(f"  seed {seed}: {text!r}")
    n_different = len(set(completions))
    word = "completion" if n_different == 1 else "completions"
    print(f"  -> {n_different} different {word} out of {len(completions)}")


def main():
    # The tokeniser cuts text into tokens, the model predicts the next one. Both download from
    # the Hugging Face Hub on the first run and are cached afterwards.
    tok = AutoTokenizer.from_pretrained("gpt2")
    model = AutoModelForCausalLM.from_pretrained("gpt2")
    model.eval()  # Use the model, do not train it.

    # Turn the prompt into token IDs, and note how long it is, so the prompt can be stripped
    # back off the output and only the generated part printed.
    inputs = tok(PROMPT, return_tensors="pt")
    prompt_len = inputs["input_ids"].shape[-1]

    def generate(temperature, top_p, seed):
        """Produce one completion. The seed fixes every random choice, so the same seed at the
        same settings always gives the same text."""
        set_seed(seed)
        with torch.no_grad():  # Nothing is being trained, so do not track gradients.
            out = model.generate(
                **inputs,
                do_sample=True,  # Sample a token, instead of always taking the likeliest one.
                temperature=temperature,
                top_p=top_p,
                # top_k is left unset on purpose, and unset is not the same as "no
                # shortlist": transformers still cuts one unless you pass top_k=0. That
                # is why a very high temperature here reads odd rather than becoming
                # word salad. A default nobody set is still a setting.
                max_new_tokens=N_NEW_TOKENS,
                pad_token_id=tok.eos_token_id,
            )
        text = tok.decode(out[0][prompt_len:], skip_special_tokens=True)
        return text.replace("\n", " ").strip()

    print(f'Model: gpt2. Prompt: "{PROMPT}"')
    print(f"Every completion below continues that prompt with {N_NEW_TOKENS} more tokens.")

    # --- Part 1: nothing changes except the random seed ---
    print(f"\n=== {N_REPEATS} repeats at temperature=1.0, top_p=1.0 ===")
    print("Same prompt, same settings, same model. Only the seed is different.")
    report([generate(1.0, 1.0, seed) for seed in range(N_REPEATS)])

    # --- Part 2: temperature, on the same three seeds each time ---
    print("\n=== Temperature sweep at top_p=1.0 ===")
    print("Temperature reshapes the probabilities before the pick: low is peaked on the")
    print("likeliest token, high flattens the distribution out.")
    for temperature in TEMPERATURES:
        print(f"\ntemperature={temperature}")
        report([generate(temperature, 1.0, seed) for seed in range(3)])

    # --- Part 3: top-p, on those same three seeds again, so the rows are comparable ---
    print("\n=== Top-p sweep at temperature=1.0 ===")
    print("Top-p shortens the list instead of reshaping it: keep the likeliest tokens whose")
    print("probabilities add up to p, then sample from those only.")
    for top_p in TOP_PS:
        print(f"\ntop_p={top_p}")
        report([generate(1.0, top_p, seed) for seed in range(3)])

    print("\nNow change something at the top of this file and run it again.")
    print("TEMPERATURES: add a very low value, 0.05, and a very high one, 5.0. One end")
    print("changes the completions much more than the other. Write down which end, and")
    print("what you think is stopping the other one.")
    print('PROMPT: a more predictable one, "2 + 2 =" for example, should give fewer')
    print("different completions at the same settings, because the model's own")
    print("distribution is already narrow.")


if __name__ == "__main__":
    main()
