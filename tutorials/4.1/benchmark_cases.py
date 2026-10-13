"""Block 4.2's twenty-case mini benchmark: two-number addition, the toy agent's own `add` tool.

Below assessment complexity on purpose, per `course-overview.md`: the system under test is the
toy agent, and the measure (exact numeric match) is provided, not designed by the student.
Subelement 3 asks students to choose both.

Each case varies along two axes, on purpose, per block 4.1's "systematic variation" teaching:

- **Phrasing** (five templates, cycled): should **not** change whether the answer is right.
- **Difficulty** (three tiers: easy, medium, hard): **should** change whether a pattern without a
  tool gets the answer right, since larger numbers and more decimal places are harder to hold in
  a single pass of text generation.

`TRUE_SUMS` are computed with `decimal.Decimal`, not `float`, so the benchmark's own ground truth
is exact. This matters: see `TOOL_PRECISION_STRESS_CASE` below for why the toy agent's own `add`
tool cannot make the same promise.
"""

from decimal import Decimal, localcontext

# `Decimal` rounds arithmetic to 28 significant digits by default, so the sum of two long numbers
# would get a rounded ground truth, and a correct answer would be graded wrong. Every sum and every
# grading comparison in this folder runs with room for this many digits instead.
EXACT_DIGITS = 100

PHRASINGS = [
    "What is {a} plus {b}?",
    "Add {a} and {b} together.",
    "Calculate the sum of {a} and {b}.",
    "{a} + {b} = ?",
    "If you have {a} of one thing and {b} of another, what is the total?",
]

# Appended to every case, identically, across both patterns and all phrasings. This is the
# benchmark's own "structured output" moment (block 3.1): a fixed convention makes automated
# grading possible without an LLM-as-judge, which is exactly the "simple, well-chosen measure"
# the brief asks for.
ANSWER_SUFFIX = " State your final numeric answer on its own line as: ANSWER: <number>"

# (a, b, tier). Strings where precision matters (decimals, very large integers), so a case's own
# true sum is computed from the exact text, never from a float.
RAW_CASES = [
    # Easy: 2-3 digit integers. A single-shot pattern should never miss these.
    ("23", "45", "easy"),
    ("7", "89", "easy"),
    ("456", "123", "easy"),
    ("91", "8", "easy"),
    ("34", "267", "easy"),
    ("608", "95", "easy"),
    # Medium: 4-6 digit integers, or 2-3 decimal places.
    ("3847", "6129", "medium"),
    ("128.45", "67.3", "medium"),
    ("92140", "58670", "medium"),
    ("456.72", "289.158", "medium"),
    ("700321", "49876", "medium"),
    ("62.5", "148.75", "medium"),
    ("814205", "97633", "medium"),
    # Hard: 10-16 digit integers or many decimal places, where a single pass of text generation
    # has to hold a lot more in mind at once than a 2-digit sum.
    ("482137561234", "918473298765", "hard"),
    ("58123.456789", "9276.543211", "hard"),
    ("7003210004998321", "4998123321004567", "hard"),
    ("7482910573.28471", "1029384756.19283", "hard"),
    ("999999999999999", "1", "hard"),
    ("48213756123456789", "91847329876543210", "hard"),
    # The deliberate stress case: 26 digits, well past float64's ~15-17 significant-digit
    # precision. See TOOL_PRECISION_STRESS_CASE's own note below: this case is not really testing
    # the model at all once the tool is involved, it is testing the tool's own JSON schema.
    ("48213756123456789012345678", "91847329876543210987654321", "hard"),
]

assert len(RAW_CASES) == 20, f"expected 20 cases, got {len(RAW_CASES)}"

TOOL_PRECISION_STRESS_CASE_NOTE = """
The last case (26-digit addends) was included on purpose, after a real run during this block's
own build surfaced a genuine confound: the toy agent's `add` tool declares its input schema as
`{"a": float, "b": float}` (block 3.1's own code). JSON itself has no digit limit, but on the way
into the tool the numbers are read as IEEE 754 doubles, which hold about 15 to 17 significant
decimal digits and every whole number exactly only up to 2**53, a 16-digit number. A real run on
this exact case showed the model correctly proposing
`add(4.821375612345679e+25, 9.18473298765432e+25)`, the tool correctly (given its own schema)
returning `1.4006108599999998e+26`, and the model's own final answer catching the discrepancy and
stating the mathematically exact sum instead, unprompted. That is a genuine result, but it is not
a clean measurement of the tool-loop pattern's reliability: past this digit count, the benchmark
is measuring the `add` tool's own schema, the exact "evaluating the scaffolding" trap this block
names as a threat to validity. See the deck's own "What the numbers do not show" section.
"""


def build_cases() -> list[dict]:
    """Render each raw case into a full prompt, cycling phrasing templates independently of
    difficulty tier, so phrasing and difficulty are not confounded with each other."""
    cases = []
    for i, (a, b, tier) in enumerate(RAW_CASES):
        template = PHRASINGS[i % len(PHRASINGS)]
        question = template.format(a=a, b=b) + ANSWER_SUFFIX
        with localcontext() as ctx:
            ctx.prec = EXACT_DIGITS
            true_sum = Decimal(a) + Decimal(b)
        cases.append(
            {
                "id": i,
                "a": a,
                "b": b,
                "tier": tier,
                "phrasing_index": i % len(PHRASINGS),
                "question": question,
                "true_sum": str(true_sum),
            }
        )
    return cases


if __name__ == "__main__":
    for case in build_cases():
        print(case)
