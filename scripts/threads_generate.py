"""Ask Claude for one day's text-only Threads tip and validate it against Margot's content rules."""
from __future__ import annotations

import json
import re

import anthropic

from generate import BANNED, MODEL, PILLARS, SIGNOFF, InvalidPost, clean

MAX_CHARS = 450  # Threads allows 500; stay under it with room to spare

# Different shapes of post so a week of tips doesn't all read the same.
FORMATS = [
    "One small step: name the step, then say how long it takes.",
    "A gentle myth-buster: 'You don't have to ...' followed by what to do instead.",
    "A two-minute checklist of 3 short lines (plain lines, no bullet symbols, start each with a verb).",
    "A calm question to ask yourself this week, then one line on how to act on the answer.",
    "A 'do this, not that' swap that makes the step feel lighter.",
    "A short permission slip: something the reader is allowed to do slowly, plus the tiny first move.",
    "A tip with a made-up example in one line (say 'made-up numbers' if you use any).",
]

# Mention the offer on two days a week only; the other days are pure tip.
OFFERS = {
    0: "Add one soft line near the end: the free Three Numbers Starter Sheet is at the link in bio.",
    4: "Add one soft line near the end: the $17 Day Zero Workbook is at the link in bio.",
}
NO_OFFER = "Do not mention any product, sheet, workbook or link today. Pure tip."

SYSTEM = f"""You write short, text-only Threads posts for Margot Ellison (@margotdayzero), a 41-year-old
creator who helps women start over financially after divorce. Her tagline is "Zero is a
starting line." Her sign-off is "{SIGNOFF}" Her voice is warm, steady, a little dry,
friendly: a big sister who has been through it. Never preachy, never salesy, never hypey.
She talks to the reader as "you". Short sentences. Plain words. No jargon without a quick
explanation.

Her method: the Three Numbers (what's coming in, what goes out, how many months you could keep
going), then Keep, Cut, Earn, Build. The Worth-It Rule: protect what's worth it first.

Each post is ONE practical tip a reader can act on in about twenty minutes or less. It should
read like a thought from a friend, not an ad or a lecture. Plain text only, written to be read
in a feed, with short lines and blank lines between them.

Hard rules:
- The whole post is at most {MAX_CHARS} characters, including line breaks and the sign-off.
- No emoji, no hashtags, no links, no special symbols.
- Never use em dashes or en dashes. Use commas or periods.
- The post ends with the sign-off "{SIGNOFF}" as its own last line.
- Never say or imply Margot is AI, an AI creator, a bot, a persona or generated. Never mention
  AI tools.
- General education only. Never give personalized financial, legal or tax advice. Never tell
  the reader what to invest in. No stocks, crypto, funds or specific products. For big
  decisions (settlements, taxes, investing, legal questions) say a licensed professional can
  help with the details.
- No made-up statistics, laws, limits, interest rates, dates or study results. If you use
  numbers, they are plainly made-up examples. Keep any factual claim general and safe.
- No income claims, no results promises, no guarantees, no get-rich language, no "financial
  freedom", no "passive income". Never promise what the reader will earn, save or achieve.
- Do not invent personal stories or human-only experiences for Margot (no "when my marriage
  ended I...", no kids, no specific past events, no amounts she earned or saved). Speak to the
  reader.
- Do not repeat a topic or hook from the "recently posted" list."""

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "text": {"type": "string"},
    },
    "required": ["topic", "text"],
    "additionalProperties": False,
}

HASHTAG_OR_LINK = re.compile(r"(^|\s)#\w|https?://|www\.", re.I)


def validate(post: dict, needs_link_in_bio: bool) -> dict:
    text = clean(post["text"], emoji=True)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    post["topic"] = clean(post["topic"], emoji=True)
    if not text.rstrip().endswith(SIGNOFF):
        raise InvalidPost(f'the post must end with "{SIGNOFF}" as its own last line')
    if len(text) > MAX_CHARS:
        raise InvalidPost(f"the post is {len(text)} characters; it must be {MAX_CHARS} or fewer")
    if len(text) < 80:
        raise InvalidPost("the post is too short to be a useful tip")
    if HASHTAG_OR_LINK.search(text):
        raise InvalidPost("no hashtags or links")
    if needs_link_in_bio and "link in bio" not in text.lower():
        raise InvalidPost('today the post must softly mention the offer with "link in bio"')
    if not needs_link_in_bio and "link in bio" in text.lower():
        raise InvalidPost("today the post must not mention the link in bio")
    m = BANNED.search(json.dumps({"topic": post["topic"], "text": text}, ensure_ascii=False))
    if m:
        raise InvalidPost(f"contains blocked wording: {m.group(0)!r}")
    post["text"] = text
    return post


def generate(weekday: int, day_number: int, recent_topics: list[str], date_label: str) -> dict:
    client = anthropic.Anthropic()
    offer = OFFERS.get(weekday, NO_OFFER)
    fmt = FORMATS[day_number % len(FORMATS)]
    recent = "\n".join(f"- {t}" for t in recent_topics[-60:]) or "- (none yet)"
    user = (
        f"Write the Threads post for {date_label}.\n"
        f"Content pillar: {PILLARS[weekday]}\n"
        f"Shape of the post: {fmt}\n"
        f"{offer}\n\n"
        f"Recently posted (do not repeat, including on Instagram):\n{recent}"
    )
    last_err = None
    for _ in range(3):
        content = user + (f"\n\nYour previous attempt was rejected: {last_err}. Fix that." if last_err else "")
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=4000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=[{"role": "user", "content": content}],
            output_config={"effort": "medium", "format": {"type": "json_schema", "schema": SCHEMA}},
        )
        if resp.stop_reason == "refusal":
            last_err = "the request was declined; pick a different, everyday topic"
            continue
        if resp.stop_reason == "max_tokens":
            last_err = "the answer was cut off; keep it shorter"
            continue
        text = next(b.text for b in resp.content if b.type == "text")
        try:
            return validate(json.loads(text), needs_link_in_bio=weekday in OFFERS)
        except (InvalidPost, json.JSONDecodeError) as e:
            last_err = str(e)
    raise InvalidPost(f"gave up after 3 attempts: {last_err}")
