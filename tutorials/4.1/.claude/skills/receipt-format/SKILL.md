---
name: receipt-format
description: Formats the result of an addition as a fixed-width TOY AGENT RECEIPT with the two values, a TOTAL and a Ref line. Use when the user asks to see, show, print or format a sum or calculation result as a receipt, a printout or a slip. Do not use for plain sums, or for bills and totals where no receipt or printout is asked for.
---

# Receipt formatting

Format the final answer exactly like this, inside a fenced code block so the layout is not
reflowed:

```
============================
      TOY AGENT RECEIPT
============================
  Value 1                 <first operand>
  Value 2                 <second operand>
----------------------------
  TOTAL                   <result>
============================
  Ref: TA-<result>-<first operand>
```

Fill in the angle-bracket fields from the actual calculation. Add no date, no name and no other
text inside the code block.
