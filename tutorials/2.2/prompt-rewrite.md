# Tutorial Part 2: rewrite a prompt

Vague prompt: "Write something about my trip."

## Output A (vague, no changes)

Trips are a wonderful way to step outside your everyday routine and experience
something new. Whether it's the food, the people, or the sights, travel has a
way of leaving a lasting impression. Every journey brings its own mix of
memorable moments and small surprises that make it worth looking back on.

## Principles applied: specificity + decomposition

### Step 1 (decomposition): get the raw material first

Prompt: "List five specific, distinct moments from a trip to Bali and
Indonesia in August 2026: one about food, one about a mistake or unexpected
delay, one about a person, one about a place, one about something that
surprised you. One line each."

1. Food: fried prawn at what's apparently the biggest Chinese restaurant in
   all of Indonesia, in Jakarta -- didn't expect it to be that good.
2. Mistake: booked an Uber to a beach in Bali that took far longer than
   expected, missed the swim -- but the sunset from there was still worth it.
3. Person: caught up with friends originally known from church in Bristol,
   now back living in Indonesia, though their visas meant they had to leave
   again soon after.
4. Place: Bali itself, which stuck with him more than anywhere else on the
   trip.
5. Surprise: the visible economic divide -- his first time in a developing
   country, and the unfairness of it was hard to shake.

### Step 2 (specificity): shape it into the actual output

Prompt: "Turn these five into a 3-sentence Instagram caption, upbeat tone,
one emoji, no cliches like 'unforgettable' or 'hidden gem'."

Output B:

> Missed the swim after an Uber ride to the beach ran long, but the sunset
> that greeted us instead wasn't a bad trade. Best meal of the trip was
> fried prawn at the biggest Chinese restaurant in Indonesia -- in Jakarta,
> of all places. Got to see old friends from Bristol before their visas
> called them back to Indonesia for good, which made Bali the one place on
> the trip I didn't want to leave.

## Which principle did the most work

Specificity constrained the format so hard it filtered out the most
substantive item on the list (the economic-divide moment doesn't fit
"upbeat, one emoji, no cliches"), while decomposition is what surfaced that
moment in the first place. So the two principles pulled in opposite
directions here, not the same one -- specificity shaped what made it in,
decomposition is what almost didn't.
