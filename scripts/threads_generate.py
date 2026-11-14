"""Ask Claude for one day's text-only Threads tip and validate it against Margot's content rules."""
from __future__ import annotations

import json
import re

import anthropic

from generate import BANNED, MODEL, PILLARS, SIGNOFF, InvalidPost, clean

MAX_CHARS = 450  # Threads allows 500; stay under it with room to spare

# Different shapes of post so a week of tips doesn't all read the same.
FORMATS = [
    "One small step told conversationally: what to do, why it helps, how long it takes.",
    "A gentle myth-buster: 'You don't have to ...' followed by what to do instead.",
    "Talking a friend through a tiny task, step by step, in flowing sentences (no bullets).",
    "A calm question to ask yourself this week, then how to act on the answer.",
    "A 'do this, not that' swap that makes the step feel lighter.",
    "A short permission slip: something the reader is allowed to do slowly, plus the tiny first move.",
    "A tip with a made-up example (say 'made-up numbers' if you use any).",
]

# The account's goal is to sell the workbook and grow a following. Offer days (Mon, Wed, Fri, Sun)
# give a tip and then softly point to a product. Growth days (Tue, Thu, Sat) are pure value written
# to be saved, shared or replied to, with no product mention.
OFFERS = {
    0: "Near the end, softly point to the free Three Numbers Starter Sheet (a one-page worksheet, free) at the link in bio.",
    2: "Near the end, softly point to the $17 Day Zero Workbook (32 pages: the Three Numbers, Where It Went, Keep Cut Earn Build, The First Hour, the Monthly Twenty with a 12-month tracker, plus bonuses: Fifteen-Minute Start, Year-at-a-Glance Bill Tracker, Dreaded Call Scripts, Questions for a Money Helper) at the link in bio. Name ONE specific part that fits today's tip. Do not describe anything that is not in this list.",
    4: "Near the end, softly point to the $17 Day Zero Workbook (32 pages: the Three Numbers, Where It Went, Keep Cut Earn Build, The First Hour, the Monthly Twenty with a 12-month tracker, plus bonuses: Fifteen-Minute Start, Year-at-a-Glance Bill Tracker, Dreaded Call Scripts, Questions for a Money Helper) at the link in bio. Name ONE specific part that fits today's tip. Do not describe anything that is not in this list.",
    6: "Near the end, softly point to the free Three Numbers Starter Sheet (a one-page worksheet, free) at the link in bio.",
}
NO_OFFER = (
    "Do not mention any product, sheet, workbook or link today. This is a growth post: write it so a "
    "reader wants to save it, send it to a friend, or reply. End the body (before the sign-off) with a "
    "simple, easy-to-answer question or a line like 'Save this for later' or 'Send this to a friend who needs it'."
)
# On these days the post must invite a reply, save or share (checked below).
GROWTH_DAYS = {1, 3, 5}
ENGAGE = re.compile(r"\?|follow|save this|share|send this|reply|below", re.I)

SYSTEM = f"""You write short, text-only Threads posts for Margot Ellison (@margotdayzero), a 41-year-old
creator who helps women start over financially after divorce. Her tagline is "Zero is a
starting line." Her sign-off is "{SIGNOFF}" Her voice is warm, steady, a little dry,
friendly: a big sister who has been through it. Never preachy, never salesy, never hypey.
She talks to the reader as "you". Plain words. No jargon without a quick explanation.

HOW IT SOUNDS: like a warm, real woman talking to a friend over coffee, not a list of tips.
Conversational and natural, with contractions ("you're", "don't", "it's"), full flowing sentences
and a bit of dry humor. Not choppy: no stacks of fragments, no one-line-per-sentence formatting.
Write one to three short paragraphs.

CONTEXT: a stranger who has never seen the account must instantly understand who it's for.
Most posts speak plainly to women starting over or rebuilding their lives, especially after a
divorce ("if you're starting over after a divorce", "rebuilding your life", "whether you're newly
divorced or years in"). Some can widen to anyone starting over from wherever they are, divorced
or not. Say it in the first sentence or two, in natural words, not as a label.

Her method: the Three Numbers (what's coming in, what goes out, how many months you could keep
going), then Keep, Cut, Earn, Build. The Worth-It Rule: protect what's worth it first.

The account's goals are to grow a following of women starting over financially and to sell her
$17 Day Zero Workbook, so every post should be easy to relate to, worth saving or sharing, and
honest. Selling is gentle: one soft line, never pushy, no fake urgency, no testimonials, no
claims about results.

Each post is ONE practical tip a reader can act on in about twenty minutes or less. It should
read like a thought from a friend, not an ad or a lecture. Plain text only.

First person: she may share opinions and her method ("here's what I'd do first", "in my
method", "I made a free one-page sheet"). She must NOT claim specific life events or results of
her own (see the rules below).

Hard rules:
- The whole post is between 280 and {MAX_CHARS} characters, including line breaks and the sign-off.
- No emoji, no hashtags, no links, no special symbols.
- NEVER use a contrast structure to make a point: no "it's not X, it's Y", "not just X but Y",
  "X isn't Y, it's Z", "no X, no Y, just Z", "less about X, more about Y", "rather than", "stop X, start Y",
  "doesn't mean X, it means Y". State only the true half as a plain claim, once.
- No "Here's the thing", "Let's be honest", "Let that sink in", no tidy motivational moral at the end,
  no rhetorical triplets for rhythm (a plain list of 2 or 4 things is fine), no stacked one-line
  paragraphs. Do not use the words journey, navigate, unlock, empower, resilience, transform or thrive.
- Every post needs ONE concrete anchor: a specific object, form, bill, time of day or small task
  (the mail still addressed to two people, a store card you forgot about, the streaming login, the
  junk drawer of statements, a utility bill, the password you reuse). Take one plain position and
  vary sentence length naturally.
- Never use em dashes or en dashes. Use commas or periods.
- Offer days end with the sign-off "{SIGNOFF}" as its own last line. Growth days end with one specific
  question (the sign-off is optional there). Never stack a motivational line before the sign-off.
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
  ended I...", no kids, no specific past events, no amounts she earned or saved, no "I rebuilt
  my finances in a year"). Speak to the reader and share method and opinion only.
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

from aitells import NEG, TELLS  # noqa: F401  (shared with the Instagram writer)

HASHTAG_OR_LINK = re.compile(r"(^|\s)#\w|https?://|www\.", re.I)


def validate(post: dict, needs_link_in_bio: bool, needs_engagement: bool = False) -> dict:
    needs_signoff = not needs_engagement  # growth posts may end on a question instead
    text = clean(post["text"], emoji=True)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    post["topic"] = clean(post["topic"], emoji=True)
    if needs_signoff and not text.rstrip().endswith(SIGNOFF):
        raise InvalidPost(f'the post must end with "{SIGNOFF}" as its own last line')
    if not needs_signoff and not (text.rstrip().endswith(SIGNOFF) or text.rstrip().endswith("?")):
        raise InvalidPost(f'a growth post must end with a question or with "{SIGNOFF}"')
    for rx, label in TELLS:
        m = rx.search(text)
        if m:
            raise InvalidPost(f"it contains {label}: {m.group(0)!r}. Rewrite that part as one plain true statement")
    if len(text) > MAX_CHARS:
        raise InvalidPost(f"the post is {len(text)} characters; it must be {MAX_CHARS} or fewer")
    if len(text) < 250:
        raise InvalidPost("the post is too short to be a useful tip")
    if HASHTAG_OR_LINK.search(text):
        raise InvalidPost("no hashtags or links")
    if needs_link_in_bio and "link in bio" not in text.lower():
        raise InvalidPost('today the post must softly mention the offer with "link in bio"')
    if not needs_link_in_bio and "link in bio" in text.lower():
        raise InvalidPost("today the post must not mention the link in bio")
    if needs_engagement and not ENGAGE.search(text):
        raise InvalidPost("today the post must invite a reply, a save or a share (a question works well)")
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
            return validate(json.loads(text), needs_link_in_bio=weekday in OFFERS, needs_engagement=weekday in GROWTH_DAYS)
        except (InvalidPost, json.JSONDecodeError) as e:
            last_err = str(e)
    raise InvalidPost(f"gave up after 3 attempts: {last_err}")
