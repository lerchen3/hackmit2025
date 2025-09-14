# Given: questions database; new question
# compute embedding of the new question
# check similar top-k of new question
# run (new question, similar question candidate) through llm to check whether the exact same or not
# prompt:
"""Fundamentally, are these two solutions the same? They need to use the all of the exact same ideas, the same technique, and the same means of execution.

Don't overthink it! It should be obvious whether or not they're doing the same thing or not: Okay reasons are, say, "Solution 1 uses length XY while solution 2 does not; no."

Return one word: "yes" or "no", nothing else. I forbid you from thinking too much or analyzing the solutions too much.
"""