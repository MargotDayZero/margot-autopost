"""Ask Claude for one day's carousel and validate it against Margot's content rules."""
from __future__ import annotations

import json
import re

import anthropic

from aitells import find_tell

MODEL = "claude-opus-5-5"

# Content pillars rotate by weekday (Monday = 0), drawn from Margot's framework.
PILLARS = [
    "The Three Numbers (what's coming in, what goes out, how many months you could keep going). Boring Money Monday.",
    "KEEP: deciding what is worth keeping on purpose (the Worth-It Rule: protect what's worth it first), without guilt.",
    "CUT: finding quiet leaks (autopay, subscriptions, things nobody uses) and how to look at them calmly.",
    "EARN: small, realistic ways to bring money in or make a skill pay, with no promises about amounts.",
    "BUILD: the first-hour setup and slow foundations (list your accounts, pull your credit report, change passwords, list bills, a small cushion).",
    "STARTING OVER: the feelings and the small first moves (the 2 A.M. math, 'where did the money go, not why', permission to go slowly).",
    "THE MONTHLY TWENTY: a gentle weekly or monthly reset, looking at your three numbers again, one small step.",
]

# Weekday offers: mostly the free sheet, the paid workbook twice a week.
OFFERS = [
    "free",  # Mon
    "free",  # Tue
    "free",  # Wed
    "free",  # Thu
    "workbook",  # Fri
    "free",  # Sat
    "workbook",  # Sun
]
OFFER_TEXT = {
    "free": "the free Three Numbers Starter Sheet (a one-page worksheet, free at her Stan store, link in bio)",
    "workbook": "The Day Zero Workbook (a 32-page guide, $17, at her Stan store, link in bio), mentioned gently and never pushy",
}

# Candid, medium-wide cover photos of Margot busy, never looking at the camera.
COVER_MOODS = ["laptop", "notebook", "coffee", "phone", "planner", "reading", "papers", "evening"]
# laptop: typing on her laptop at the office desk | notebook: writing by hand
# coffee: leaning on the kitchen counter with a mug | phone: reading her phone on the sofa
# planner: planning with a planner and sticky notes | reading: curled up with a book
# papers: sorting statements and mail at the kitchen table | evening: closing the laptop, wrapping up

SYSTEM = """You write Instagram carousels for Margot Ellison (@margotdayzero), a 41-year-old
creator who helps women start over financially after divorce. Her tagline is "Zero is a
starting line." Her sign-off is "Day one counts." Her voice is warm, steady, a little dry,
friendly: a big sister who has been through it. Never preachy, never salesy, never hypey.
She talks to the reader as "you". Short sentences. Plain words. No jargon without a quick
explanation.

Her method: the Three Numbers (what's coming in, what goes out, how many months you could keep
going), then Keep, Cut, Earn, Build. The Worth-It Rule: protect what's worth it first.
Her line: "All you need is a phone or a laptop."

Every carousel teaches ONE small, practical, specific step a reader can do in about twenty
minutes or less, with a calm tone that makes the reader feel capable, not behind.

Structure (5 to 8 slides total):
1. One "cover" slide: a scroll-stopping, gentle hook title (max 50 characters, it must fit on two lines) and a short
   subtitle (max 40 characters). Pick the cover photo mood that best fits the topic:
   laptop (typing at her desk), notebook (writing by hand), coffee (relaxed with a mug),
   phone (on her phone), planner (planning with sticky notes), reading (with a book),
   papers (sorting statements and mail), evening (closing the laptop, wrap-up or reset topics).
2. 3 to 6 middle slides of type "text" or "list". A "text" slide has a title and short body.
   A "list" slide has a title and 3 to 5 short items (a step list or checklist).
3. One final "cta" slide: invite the reader to save the post and point, softly, to the offer
   named in the request via the link in bio. The cta slide body must end with the words
   "Day one counts."

Hard rules:
- Slide text must not contain emoji or special symbols (they cannot be rendered). Captions may
  use at most one simple emoji.
- Never use em dashes or en dashes anywhere. Use commas or periods.
- Never say or imply Margot is AI, an AI creator, an AI character, a bot, a persona or generated.
  The account discloses that separately. Never mention AI tools at all.
- General education only. Never give personalized financial, legal or tax advice. Never tell
  the reader what to invest in. No stocks, crypto, funds, or specific products. For big
  decisions (settlements, taxes, investing, legal questions) say a licensed professional can
  help with the details.
- No made-up statistics, laws, limits, interest rates, dates or study results. If you use
  numbers, say they are made-up examples ("Example with made-up numbers"). Keep any factual
  claim general and safe (for example: you can ask each credit bureau for your report, check
  annualcreditreport.com for the current rules).
- No income claims, no results promises, no guarantees, no get-rich language, no "financial
  freedom", no "passive income". Never promise what the reader will earn, save or achieve.
- Do not invent personal stories or human-only experiences for Margot (no "when my marriage
  ended I...", no kids, no specific past events, no amounts she earned or saved). Speak to the
  reader. A line like "I wish someone had handed me this" is fine; specific invented history
  is not.
- Be kind about the divorce context without assuming the reader's situation or being
  dramatic. If a topic touches someone controlling the reader's money, you may mention the
  National Domestic Violence Hotline, 1-800-799-7233, in the caption only.
- Keep slide text short: titles max 60 characters, body max 200 characters, list items max
  70 characters each.
- NEVER use a contrast structure to make a point, on slides or in the caption: no "it's not X, it's Y",
  "not just X but Y", "X isn't Y, it's Z", "Not this. Not that. Just this.", "no more X, no more Y",
  "less about X, more about Y", "rather than", "stop X, start Y", "doesn't mean X, it means Y".
  State only the true half as one plain claim. Also avoid "Here's the thing", "Let's be honest",
  rhetorical triplets for rhythm, tidy motivational morals, and the words journey, navigate, unlock,
  empower, resilience, transform, thrive. Give each post one concrete anchor (a specific bill, form,
  statement, account, time of day or small task) and sound like a person talking, not a template.
- Do not repeat a topic or hook from the "recently posted" list.
- Caption: a gentle hook line, 2 to 4 short lines explaining the step, a save reminder, a
  pointer to the offer via "link in bio", and the sign-off "Day one counts." as its own line.
  Do not include the disclaimer line or hashtags in the caption text (they are added
  automatically). Put 4 or 5 relevant lowercase hashtags in the hashtags field."""

SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "cover_title": {"type": "string"},
        "cover_subtitle": {"type": "string"},
        "cover_mood": {"type": "string", "enum": COVER_MOODS},
        "slides": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["text", "list", "cta"]},
                    "kicker": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "items": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["type", "kicker", "title", "body", "items"],
                "additionalProperties": False,
            },
        },
        "caption": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["topic", "cover_title", "cover_subtitle", "cover_mood", "slides", "caption", "hashtags"],
    "additionalProperties": False,
}

EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF\U0000FE0F\U0000200D\U00002B00-\U00002BFF]"
)
DASHES = re.compile(r"\s*[—–]\s*")

# Anything here makes the draft fail and Claude is asked to try again.
BANNED = re.compile(
    r"\b(ai|a\.i\.|artificial intelligence|chatgpt|bot|persona|ai[- ]generated)\b"
    r"|guarantee|get rich|passive income|risk[- ]free|double your|financial freedom"
    r"|\bmake \$\d|\bearn \$\d|you will (earn|make|be rich)|invest in |stock tip|crypto|bitcoin"
    r"|\bbuy (this|these) stock|\b(my|our) (kids|children|ex|divorce)\b|when i (got divorced|left)",
    re.I,
)

DISCLAIMER = "General education, not financial advice."
SIGNOFF = "Day one counts."


class InvalidPost(Exception):
    pass


def clean(text: str, emoji: bool) -> str:
    text = DASHES.sub(", ", text) if text else text
    if emoji:
        text = EMOJI.sub("", text)
    return text.strip()


def validate(post: dict) -> dict:
    mids = [s for s in post["slides"] if s["type"] in ("text", "list")]
    ctas = [s for s in post["slides"] if s["type"] == "cta"]
    if not (3 <= len(mids) <= 6):
        raise InvalidPost(f"expected 3-6 middle slides, got {len(mids)}")
    if len(ctas) != 1 or post["slides"][-1]["type"] != "cta":
        raise InvalidPost("exactly one cta slide, last")
    if not any(s["type"] == "list" and 3 <= len(s["items"]) <= 5 for s in mids):
        raise InvalidPost("needs at least one list slide with 3 to 5 items")

    limits = {"title": 70, "body": 230, "kicker": 40}
    for s in post["slides"]:
        for k, lim in limits.items():
            s[k] = clean(s[k], emoji=True)
            if len(s[k]) > lim:
                raise InvalidPost(f"{k} too long ({len(s[k])}>{lim}): {s[k][:40]}...")
        s["items"] = [clean(i, emoji=True) for i in s["items"]]
        if any(len(i) > 80 for i in s["items"]):
            raise InvalidPost("a list item is longer than 80 characters")
        if s["type"] != "list":
            s["items"] = []
        if s["type"] == "list" and not (3 <= len(s["items"]) <= 5):
            raise InvalidPost("a list slide needs 3 to 5 items")
    if not post["slides"][-1]["body"].rstrip().endswith(SIGNOFF):
        raise InvalidPost(f'the cta slide body must end with "{SIGNOFF}"')

    post["cover_title"] = clean(post["cover_title"], emoji=True)
    post["cover_subtitle"] = clean(post["cover_subtitle"], emoji=True)
    if len(post["cover_title"]) > 70 or len(post["cover_subtitle"]) > 55:
        raise InvalidPost("cover title or subtitle too long")
    post["topic"] = clean(post["topic"], emoji=True)

    caption = clean(post["caption"], emoji=False)
    if SIGNOFF not in caption:
        raise InvalidPost(f'the caption must include the sign-off "{SIGNOFF}"')
    if "link in bio" not in caption.lower():
        raise InvalidPost('the caption must point to the offer with "link in bio"')
    post["caption"] = caption

    # No machine-sounding contrast shapes ("not X, it's Y", "Not this. Not that.") in any field.
    fields = [post["cover_title"], post["cover_subtitle"], post["caption"]]
    for sl in post["slides"]:
        fields += [sl["kicker"], sl["title"], sl["body"], *sl["items"]]
    for f in fields:
        hit = find_tell(f)
        if hit:
            raise InvalidPost(f"it contains {hit[0]}: {hit[1]!r}. Rewrite that part as one plain true statement")

    all_text = json.dumps(post, ensure_ascii=False)
    m = BANNED.search(all_text)
    if m:
        raise InvalidPost(f"contains blocked wording: {m.group(0)!r}")
    post["hashtags"] = [("#" + h.lstrip("#")).lower().replace(" ", "") for h in post["hashtags"]][:5]
    return post


def generate(pillar: str, offer: str, recent_topics: list[str], date_label: str) -> dict:
    client = anthropic.Anthropic()
    recent = "\n".join(f"- {t}" for t in recent_topics[-60:]) or "- (none yet)"
    user = (
        f"Write the carousel for {date_label}.\n"
        f"Today's content pillar: {pillar}\n"
        f"Offer to mention softly on the last slide and in the caption: {OFFER_TEXT[offer]}\n\n"
        f"Recently posted (do not repeat):\n{recent}"
    )
    last_err = None
    for attempt in range(3):
        msgs = [{"role": "user", "content": user}]
        if last_err:
            msgs[0]["content"] += f"\n\nYour previous attempt was rejected: {last_err}. Fix that."
        resp = client.beta.messages.create(
            model=MODEL,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            system=SYSTEM,
            messages=msgs,
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
            return validate(json.loads(text))
        except (InvalidPost, json.JSONDecodeError) as e:
            last_err = str(e)
    raise InvalidPost(f"gave up after 3 attempts: {last_err}")
