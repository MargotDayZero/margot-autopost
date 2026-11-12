"""Render a carousel (list of slide dicts) into 1080x1350 JPEGs with Pillow, in Margot's look.

Slide types:
  cover - full-bleed photo of Margot (upper half), warm dark gradient below, big title + subtitle
  text  - cream card: kicker, title, body
  list  - cream card: kicker, title, numbered items
  cta   - cream card: title, body, "Link in bio", disclaimer
Fonts: Gelasio (open license, a close match for Georgia) in assets/fonts/. Falls back to Georgia
or DejaVu Serif for local previews only.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "assets" / "fonts"

W, H, M = 1080, 1350, 92
CREAM = (251, 246, 236)
OATMEAL = (239, 230, 214)
CAMEL = (184, 137, 90)
GOLD = (184, 150, 74)
SAGE = (124, 144, 112)
TERRA = (180, 98, 63)
INK = (58, 49, 40)
INK_SOFT = (88, 77, 66)
MUTED = (140, 128, 114)
WHITE = (255, 252, 246)
GOLD_LIGHT = (232, 205, 150)
HANDLE = "@margotdayzero"
DISCLAIMER = "General education, not financial advice."

STATIC = {"R": "Gelasio-Regular.ttf", "B": "Gelasio-Bold.ttf", "I": "Gelasio-Italic.ttf"}
VARIABLE = {"R": ("Gelasio[wght].ttf", 400), "B": ("Gelasio[wght].ttf", 700), "I": ("Gelasio-Italic[wght].ttf", 400)}
SYSTEM_FALLBACK = {
    "R": ["/System/Library/Fonts/Supplemental/Georgia.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"],
    "B": ["/System/Library/Fonts/Supplemental/Georgia Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf"],
    "I": ["/System/Library/Fonts/Supplemental/Georgia Italic.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Italic.ttf"],
}


def font(style: str, size: int) -> ImageFont.FreeTypeFont:
    p = FONTS / STATIC[style]
    if p.exists():
        return ImageFont.truetype(str(p), size)
    name, weight = VARIABLE[style]
    p = FONTS / name
    if p.exists():
        f = ImageFont.truetype(str(p), size)
        try:
            f.set_variation_by_axes([weight])
        except Exception:
            pass
        return f
    for cand in SYSTEM_FALLBACK[style]:
        if Path(cand).exists():
            return ImageFont.truetype(cand, size)
    raise FileNotFoundError("No serif font found. Add Gelasio to assets/fonts/.")


def wrap(text: str, f: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    for para in text.split("\n"):
        if para.strip() == "":
            lines.append("")
            continue
        cur = ""
        for w in para.split(" "):
            trial = w if not cur else f"{cur} {w}"
            if f.getlength(trial) <= width:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def block_height(lines, f, spacing) -> int:
    return int(f.size * spacing) * len(lines)


def draw_lines(d, lines, f, color, x, y, spacing) -> int:
    lh = int(f.size * spacing)
    for ln in lines:
        d.text((x, y), ln, font=f, fill=color)
        y += lh
    return y


def spaced(d, xy, text, f, fill, tracking=4):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking


def spaced_width(text, f, tracking=4) -> float:
    return sum(f.getlength(c) + tracking for c in text) - tracking


def cover(slide: dict, page: str) -> Image.Image:
    photo = Image.open(ROOT / slide["photo"]).convert("RGB")
    scale = max(W / photo.width, H / photo.height)
    photo = photo.resize((round(photo.width * scale), round(photo.height * scale)), Image.LANCZOS)
    left = (photo.width - W) // 2
    top = int((photo.height - H) * 0.0)  # keep the top: she sits in the upper half
    img = photo.crop((left, top, left + W, top + H))

    # Warm dark gradient from the lower half so the title always reads.
    grad = Image.new("L", (1, H), 0)
    start = int(H * 0.42)
    for y in range(H):
        a = 0 if y < start else int(246 * ((y - start) / (H - start)) ** 0.85)
        grad.putpixel((0, y), a)
    shade = Image.new("RGB", (W, H), (42, 34, 27))
    img = Image.composite(shade, img, grad.resize((W, H)))

    d = ImageDraw.Draw(img)
    tw = W - 2 * M
    sf = font("I", 40)
    # Largest title size that fits in two lines (three at the smallest), so the title stays low
    # and clear of the photo's subject.
    for size in (74, 70, 66, 62, 58, 54):
        tf = font("B", size)
        t_lines = wrap(slide["title"], tf, tw)
        if len(t_lines) <= 2:
            break
    s_lines = wrap(slide.get("subtitle", ""), sf, tw) if slide.get("subtitle") else []
    th = block_height(t_lines, tf, 1.14)
    sh = block_height(s_lines, sf, 1.3)
    y = H - 150 - th - (sh + 44 if s_lines else 0)
    d.rectangle((M, y - 34, M + 84, y - 30), fill=GOLD)
    y = draw_lines(d, t_lines, tf, WHITE, M, y, 1.14) + 18
    if s_lines:
        draw_lines(d, s_lines, sf, GOLD_LIGHT, M, y, 1.3)
    small = font("R", 28)
    d.text((M, H - 96), HANDLE, font=small, fill=(236, 228, 216))
    d.text((W - M - small.getlength(page), H - 96), page, font=small, fill=(236, 228, 216))
    return img


def card_slide(slide: dict, page: str) -> Image.Image:
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    tw = W - 2 * M
    small = font("R", 28)
    d.text((M, 72), HANDLE, font=small, fill=MUTED)
    d.text((W - M - small.getlength(page), 72), page, font=small, fill=MUTED)
    d.line((M, 124, W - M, 124), fill=OATMEAL, width=3)

    kind = slide["type"]
    kf = font("B", 28)
    title_size = 78 if kind == "cta" else (66 if kind == "list" else 72)
    tf = font("B", title_size)
    bf = font("R", 46 if kind != "list" else 42)
    itf = font("R", 42)
    num_f = font("B", 34)

    blocks = []  # (kind, lines, font, color, spacing, gap_after)
    if slide.get("kicker"):
        blocks.append(("kicker", [slide["kicker"].upper()], kf, TERRA, 1.3, 26))
    if slide.get("title"):
        blocks.append(("title", wrap(slide["title"], tf, tw), tf, INK, 1.18, 30))
    if slide.get("body"):
        blocks.append(("body", wrap(slide["body"], bf, tw), bf, INK_SOFT, 1.5, 30))
    items = []
    if kind == "list":
        for it in slide.get("items", []):
            items.append(wrap(it, itf, tw - 96))

    item_gap = 26
    def items_h():
        return sum(max(block_height(ls, itf, 1.4), 64) for ls in items) + item_gap * max(len(items) - 1, 0)

    total = sum(block_height(b[1], b[2], b[4]) for b in blocks) + sum(b[5] for b in blocks[:-1] if b[1])
    if items:
        total += 30 + items_h()
    y = max(190, 150 + (H - 330 - total) // 2)
    if blocks and blocks[0][0] == "kicker":
        spaced(d, (M, y), blocks[0][1][0], kf, TERRA, tracking=5)
        y += int(kf.size * 1.3) + blocks[0][5]
        blocks = blocks[1:]
    for b in blocks:
        y = draw_lines(d, b[1], b[2], b[3], M, y, b[4]) + b[5]
    if items:
        y += 0
        for n, ls in enumerate(items, 1):
            ih = max(block_height(ls, itf, 1.4), 64)
            d.ellipse((M, y, M + 64, y + 64), fill=TERRA)
            nw = num_f.getlength(str(n))
            d.text((M + 32 - nw / 2, y + 10), str(n), font=num_f, fill=WHITE)
            draw_lines(d, ls, itf, INK, M + 96, y + 6, 1.4)
            y += ih + item_gap

    if kind == "cta":
        d.rectangle((M, H - 232, M + 84, H - 228), fill=GOLD)
        d.text((M, H - 208), "Link in bio", font=font("B", 38), fill=TERRA)
        d.text((M, H - 140), DISCLAIMER, font=font("I", 26), fill=MUTED)
    else:
        sw = font("I", 30)
        label = "swipe  >"
        d.text((W - M - sw.getlength(label), H - 120), label, font=sw, fill=MUTED)
    return img


def curly(v):
    if isinstance(v, str):
        return v.replace("'", "\u2019")
    if isinstance(v, list):
        return [curly(x) for x in v]
    return v


def render(slides: list[dict], out_dir: Path) -> list[Path]:
    slides = [{k: (curly(v) if k != "photo" else v) for k, v in s.items()} for s in slides]
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    n = len(slides)
    for i, s in enumerate(slides, 1):
        page = f"{i}/{n}"
        img = cover(s, page) if s["type"] == "cover" else card_slide(s, page)
        p = out_dir / f"{i:02d}.jpg"
        img.save(p, "JPEG", quality=92, optimize=True)
        paths.append(p)
    return paths


if __name__ == "__main__":
    import json

    post = json.loads(Path(sys.argv[1]).read_text())
    for p in render(post["slides"], Path(sys.argv[2])):
        print(p)
