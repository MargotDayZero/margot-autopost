"""Sentence shapes that read as machine-written. Shared by the Instagram and Threads writers."""
from __future__ import annotations

import re

# Sentence shapes that read as machine-written (contrastive reveals and friends). A post that
# matches any of these is rejected and Claude is asked to rewrite it.
NEG = r"(?:\b(?:not|isn't|aren't|wasn't|weren't|doesn't|don't|didn't|never|no)\b|n't\b)"
TELLS = [
    (re.compile(NEG + r"[^.!?\n]{0,60}[.!?;,]\s+(?:and\s+)?(?:it's|it is|it (?:\w+ )?(?:just )?means|you're|you are|you just|they're|this is|but|just|instead|more)\b", re.I),
     'a "not X, it\'s Y" contrast'),
    (re.compile(r"\bnot (?:just|only|merely)\b", re.I), '"not just X but Y"'),
    (re.compile(r"\b(?:isn't|aren't|wasn't|weren't|doesn't mean)\b[^.!?\n]{1,50}[,.]\s*\w+(?:\s\w+)?\s+(?:is|are|was|means)\b", re.I), '"X isn\'t Y, Z is Y"'),
    (re.compile(r"\b(?:no|not)\s+\w+(?:\s+\w+){0,3},\s*(?:no|not)\s+\w+[^.!?]{0,40}[,.]?\s*(?:just|only)\b", re.I), '"no X, no Y, just Z"'),
    (re.compile(r"\bless (?:about )?[^.,!?]{1,40},\s*more\b|\brather than\b", re.I), '"less X, more Y" or "rather than"'),
    (re.compile(r"(?:^|[.!?\n])\s*not\b[^.!?\n]{1,50}[.!?]\s*not\b", re.I), 'stacked "Not X. Not Y."'),
    (re.compile(r"\bno more\b[^.!?\n]{1,40}[.!?]\s*no more\b", re.I), 'stacked "No more X. No more Y."'),
    (re.compile(r"\bstop\b[^.!?]{1,50}[.!?]\s+start\b", re.I), '"Stop X. Start Y."'),
    (re.compile(r"\b(?:here's the thing|let's be honest|let that sink in|read that again|the truth is|the real (?:\w+ )?(?:is|issue|problem))\b", re.I), "a drama opener"),
    (re.compile(r"\b(?:journey|navigat\w+|unlock\w*|game[- ]changer|empower\w*|resilien\w+|transform\w*|thrive)\b", re.I), "an abstract empowerment word"),
]


def find_tell(text: str):
    """Return (label, matched text) for the first AI-sounding shape in text, or None."""
    for rx, label in TELLS:
        m = rx.search(text)
        if m:
            return label, m.group(0)
    return None
