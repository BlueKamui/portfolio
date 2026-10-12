"""Tutorial part 1b: the tokeniser probe.

What this does: runs a real tokeniser over a few short strings and prints, for each one, the
chunks the string was cut into and the ID number the model actually reads for each chunk.

What to look for:

  - a word you think of as one thing that comes out as several chunks
  - a number whose digits do not split the way column arithmetic needs them to
  - how far the character count and the token count drift apart, since tokens are the unit
    providers bill in

Run it from this folder:
    uv run --with tiktoken python probe_tokeniser.py

Then add your own strings to the EXAMPLES list below and run it again.
"""

import tiktoken

# cl100k_base is the encoding GPT-4 and GPT-3.5 use. Checked with
# tiktoken.encoding_for_model("gpt-4"), which returns exactly this name.
ENCODING = "cl100k_base"

EXAMPLES = [
    "strawberry",               # a word you would normally count letters in
    "3437 + 8123 = 11560",      # arithmetic, where digit alignment matters
    "unbelievable",             # common word, built from common parts
    "internationalization",     # long, but common enough to stay cheap
    "The cat sat on the mat.",  # ordinary text, for comparison
    "tokenization",              # technical term from the course
    "Zuko",                      # a name
    "larp",                      # a made-up word
    # Add your own here. Try a technical term, a name, and a made-up word.
]


def main():
    # Load the vocabulary once. This is the real list of chunks the model was trained on.
    enc = tiktoken.get_encoding(ENCODING)
    print(f"Tokeniser: {ENCODING}, {enc.n_vocab} chunks in its vocabulary.")
    print("A token is one chunk. It is what the model reads, and what you are billed for.")

    for text in EXAMPLES:
        # encode() returns the ID numbers. Decoding each ID on its own turns it back into the
        # piece of text it stands for, which is what makes the split visible.
        ids = enc.encode(text)
        chunks = [enc.decode([i]) for i in ids]
        print(f'\n"{text}"')
        print(f"  {len(text)} characters -> {len(ids)} tokens")
        print(f"  chunks: {chunks}")
        print(f"  ids:    {ids}")

    print("\nNow count the letters in 'strawberry' using only its chunk list, not the word.")
    print("The model has exactly that problem: it never sees the letters, only the chunks.")


if __name__ == "__main__":
    main()
