"""Builds the Dandelion Circularity website into the folder _site/.

    python build.py

Cloudflare Pages runs this automatically after every change made in /admin.
- src/      the fixed pages (Dutch and English), the menu and footer, styles and fonts
- content/  what editors change in /admin: news, calendar, videos, photo albums
- media/    photos uploaded in /admin (originals; the site gets smaller copies without camera data)
"""
import html
import io
import json
import re
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path

from PIL import Image, ImageOps

ROOT = Path(__file__).parent
SRC, CONTENT, MEDIA, OUT = ROOT / "src", ROOT / "content", ROOT / "media", ROOT / "_site"
MAX_SIDE = 1600
warnings = []

LOGO = '<img src="assets/img/logo-embleem.png" alt="" width="96" height="96">'
SEED = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 80" aria-hidden="true" class="seed">'
        '<g fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">'
        '<path d="M20 26V64"/><path d="M20 26L2 12M20 26L7 6M20 26L14 2M20 26V1M20 26L26 2M20 26L33 6M20 26L38 12"/></g>'
        '<path d="M20 62c3 4 3 10 0 16c-3-6-3-12 0-16z" fill="currentColor"/></svg>')
SUBMENUS = {"workshops": ("permacultuur", "conserveren"), "over": ("over", "missie", "doelstellingen", "visie", "kernwaarden")}
MONTHS = {"nl": "januari februari maart april mei juni juli augustus september oktober november december".split(),
          "en": "January February March April May June July August September October November December".split()}
T = {
    "nl": dict(play="Video afspelen", yt="Bekijk op YouTube", no_videos="Binnenkort staan hier onze video's.",
               no_news="Hier delen we binnenkort de ontwikkelingen in de tuin, workshopverslagen en foto's.",
               upcoming="Komende activiteiten"),
    "en": dict(play="Play video", yt="Watch on YouTube", no_videos="Our videos will appear here soon.",
               no_news="This is where we will soon share developments in the garden, workshop reports and photos.",
               upcoming="Upcoming activities"),
}


# ---------- helpers ----------

def esc(text):
    """Escape editor text for HTML (braces too, so text can never look like a template token)."""
    return html.escape(str(text or ""), quote=True).replace("{", "&#123;").replace("}", "&#125;")


def paragraphs(text):
    """Plain text from the editor: blank line = new paragraph, web addresses become links."""
    out = []
    for block in re.split(r"\n\s*\n", str(text or "").replace("\r\n", "\n")):
        if block.strip():
            e = re.sub(r"(https?://[^\s<]+[^\s<.,;:!?)\]'\"])", r'<a href="\1">\1</a>', esc(block.strip()))
            out.append("<p>" + e.replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def pick(item, field, lang):
    """The English field when filled in, otherwise the Dutch one (then marked lang="nl" on the English site)."""
    if lang == "en" and str(item.get(f"{field}_en") or "").strip():
        return item[f"{field}_en"], ""
    return item.get(field) or "", (' lang="nl"' if lang == "en" else "")


def nice_date(iso, lang):
    y, m, d = (int(x) for x in str(iso)[:10].split("-"))
    return f"{d} {MONTHS[lang][m - 1]} {y}"


def load(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError:
        return default
    except Exception as e:  # a broken file must not take the whole site down
        warnings.append(f"could not read {path.relative_to(ROOT)}: {e}")
        return default


def load_folder(name):
    items = []
    for p in sorted((CONTENT / name).glob("*.json")):
        d = load(p, None)
        if isinstance(d, dict) and re.match(r"\d{4}-\d{2}-\d{2}", str(d.get("datum", ""))):
            items.append(d)
        elif d is not None:
            warnings.append(f"skipped {p.relative_to(ROOT)}: no valid date")
    return items


# ---------- images ----------

_images = {}


def safe_name(stem):
    s = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return s or "foto"


def web_image(path):
    """'/media/x.jpg' -> ('media/x.jpg', width, height): a resized copy without camera data (location etc.) in _site."""
    if not path:
        return None
    rel = str(path).split("?")[0].lstrip("/")
    if rel in _images:
        return _images[rel]
    src = ROOT / rel
    result = None
    if not rel.startswith("media/") or not src.is_file():
        warnings.append(f"image not found: {path}")
    else:
        try:
            im = ImageOps.exif_transpose(Image.open(src))
            alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            target = OUT / Path(rel).parent / (safe_name(src.stem) + (".png" if alpha else ".jpg"))
            n = 2
            while target.exists():
                target = target.with_name(f"{safe_name(src.stem)}-{n}{target.suffix}")
                n += 1
            target.parent.mkdir(parents=True, exist_ok=True)
            if alpha:
                im.save(target, "PNG", optimize=True)
            else:
                im.convert("RGB").save(target, "JPEG", quality=82, optimize=True, progressive=True)
            result = (target.relative_to(OUT).as_posix(), im.width, im.height)
        except Exception as e:
            warnings.append(f"could not process image {path}: {e} (use JPG or PNG)")
    _images[rel] = result
    return result


def crop_ratio(im, rw, rh):
    w, h = im.size
    if w / h > rw / rh:
        nw = round(h * rw / rh)
        return im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    nh = round(w * rh / rw)
    return im.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))


# ---------- YouTube ----------

def youtube_id(url):
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})", str(url or ""))
    return m.group(1) if m else None


def youtube_thumb(vid, short):
    """Still image saved on our own site, so visitors only contact YouTube after they click play."""
    p = MEDIA / "youtube" / f"{vid}.jpg"
    if not p.exists():
        names = ("oardefault", "maxresdefault", "sddefault", "hqdefault") if short else ("maxresdefault", "sddefault", "hqdefault")
        for name in names:
            try:
                with urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=20) as r:
                    im = Image.open(io.BytesIO(r.read())).convert("RGB")
                break
            except Exception:
                continue
        else:
            warnings.append(f"no thumbnail for YouTube video {vid}")
            return None
        p.parent.mkdir(parents=True, exist_ok=True)
        crop_ratio(im, *((9, 16) if short else (16, 9))).save(p, "JPEG", quality=85)
    return web_image(f"/media/youtube/{vid}.jpg")


def videos(lang):
    t, wide, shorts = T[lang], [], []
    for v in load(CONTENT / "videos.json", {}).get("videos", []):
        vid = youtube_id(v.get("url"))
        if not vid:
            warnings.append(f"not a YouTube link: {v.get('url')}")
            continue
        short = "/shorts/" in str(v.get("url"))
        url = f"https://www.youtube.com/shorts/{vid}" if short else f"https://www.youtube.com/watch?v={vid}"
        title, la = pick(v, "titel", lang)
        thumb = youtube_thumb(vid, short)
        img = f'<img src="{thumb[0]}" alt="" width="{thumb[1]}" height="{thumb[2]}" loading="lazy">' if thumb else ""
        fig = (f'<figure class="yt yt-{"short" if short else "wide"}"><a class="yt-play" href="{url}" data-yt="{vid}" data-title="{esc(title)}">'
               f'{img}<span class="yt-icon" aria-hidden="true"></span><span class="yt-label">{t["play"]}'
               f'<span class="visually-hidden">: <span{la}>{esc(title)}</span></span></span></a>'
               f'<figcaption><span{la}>{esc(title)}</span> · <a href="{url}">{t["yt"]}</a></figcaption></figure>')
        (shorts if short else wide).append(fig)
    if not wide and not shorts:
        return f'<p>{t["no_videos"]}</p>'
    out = "\n    ".join(wide)
    if shorts:
        out += '\n    <div class="yt-shorts stack-top">\n      ' + "\n      ".join(shorts) + "\n    </div>"
    return out


# ---------- photo albums ----------

def gallery(album, lang):
    figs = []
    for item in load(CONTENT / f"fotos-{album}.json", {}).get("fotos", []):
        img = web_image(item.get("foto"))
        if not img:
            continue
        cap, cl = pick(item, "bijschrift", lang)
        alt, al = pick(item, "beschrijving", lang)
        caption = f"<figcaption{cl}>{esc(cap)}</figcaption>" if str(cap).strip() else ""
        alt_lang = al if str(alt).strip() else ""
        figs.append(f'<figure><img class="foto foto-portret" src="{img[0]}" alt="{esc(alt)}"{alt_lang} width="{img[1]}" height="{img[2]}" loading="lazy">{caption}</figure>')
    if not figs:
        return ""
    return '    <div class="gallery stack-top">\n      ' + "\n      ".join(figs) + "\n    </div>"


# ---------- news and calendar ----------

def news(lang):
    items = sorted(load_folder("nieuws"), key=lambda d: str(d["datum"]), reverse=True)
    if not items:
        return f'    <p>{T[lang]["no_news"]}</p>'
    cards = []
    for d in items:
        title, tl = pick(d, "titel", lang)
        text, xl = pick(d, "tekst", lang)
        img = web_image(d.get("foto")) if d.get("foto") else None
        alt, al = pick(d, "beschrijving", lang)
        photo = (f'<img class="foto" src="{img[0]}" alt="{esc(alt)}"{al if str(alt).strip() else ""} width="{img[1]}" height="{img[2]}" loading="lazy">'
                 if img else "")
        iso = str(d["datum"])[:10]
        cards.append(f'<article class="card news-item">{photo}<p class="news-date"><time datetime="{iso}">{nice_date(iso, lang)}</time></p>'
                     f'<h3{tl}>{esc(title)}</h3><div class="news-text"{xl}>{paragraphs(text)}</div></article>')
    return '    <div class="news-list stack-top">\n      ' + "\n      ".join(cards) + "\n    </div>"


def agenda(lang):
    today = date.today().isoformat()
    items = sorted((d for d in load_folder("agenda") if str(d["datum"])[:10] >= today), key=lambda d: str(d["datum"]))
    if not items:
        return ""
    rows = []
    for d in items:
        iso = str(d["datum"])[:10]
        title, tl = pick(d, "titel", lang)
        text, xl = pick(d, "tekst", lang)
        meta = " · ".join(esc(x) for x in (d.get("tijd"), d.get("locatie")) if str(x or "").strip())
        rows.append(f'<li class="card agenda-item" data-datum="{iso}"><p class="story-mark"><time datetime="{iso}">{nice_date(iso, lang)}</time></p>'
                    f'<h4{tl}>{esc(title)}</h4>' + (f'<p class="agenda-meta">{meta}</p>' if meta else "")
                    + (f'<div{xl}>{paragraphs(text)}</div>' if str(text).strip() else "") + "</li>")
    return (f'    <div class="agenda-upcoming stack-top"><h3>{T[lang]["upcoming"]}</h3>\n      <ul class="agenda-list">\n        '
            + "\n        ".join(rows) + "\n      </ul>\n    </div>")


# ---------- pages ----------

def switch(lang, fname):
    nl_href = fname if lang == "nl" else f"../{fname}"
    en_href = f"en/{fname}" if lang == "nl" else fname
    label = "Taal kiezen" if lang == "nl" else "Choose language"
    nl_cur = ' aria-current="true"' if lang == "nl" else ""
    en_cur = ' aria-current="true"' if lang == "en" else ""
    return (f'<div class="lang-switch" role="group" aria-label="{label}">'
            f'<a href="{nl_href}" lang="nl" hreflang="nl" aria-label="Nederlands"{nl_cur}>NL</a>'
            f'<a href="{en_href}" lang="en" hreflang="en" aria-label="English"{en_cur}>EN</a></div>')


def build(lang, target):
    target.mkdir(parents=True, exist_ok=True)
    template = (SRC / f"template-{lang}.html").read_text(encoding="utf-8")
    source = (SRC / f"pages-{lang}.html").read_text(encoding="utf-8")
    dynamic = {"{{videos}}": videos(lang), "{{gallery:conserveren}}": gallery("conserveren", lang),
               "{{gallery:tuin}}": gallery("tuin", lang), "{{nieuws}}": news(lang), "{{agenda}}": agenda(lang)}
    chunks = re.split(r"^<!--PAGE (.+?)-->\s*$", source, flags=re.M)
    names = []
    for meta, body in zip(chunks[1::2], chunks[2::2]):
        parts = [p.strip() for p in meta.split("|")]
        fname, key, desc = parts[0], parts[1], parts[-1].replace(" & ", " &amp; ")
        title = " | ".join(parts[2:-1]).replace(" & ", " &amp; ")
        page = template.replace("{{title}}", title).replace("{{desc}}", desc).replace("{{body}}", body.strip())
        page = page.replace("{{logo}}", LOGO).replace("{{seed}}", SEED).replace("{{lang}}", switch(lang, fname))
        page = re.sub(r"\{\{cur:(\w+)\}\}", lambda m: ' aria-current="page"' if m.group(1) == key else "", page)
        page = re.sub(r"\{\{subcur:(\w+)\}\}", lambda m: " is-current" if key in SUBMENUS[m.group(1)] else "", page)
        for token, value in dynamic.items():
            page = page.replace(token, value.lstrip())
        page = re.sub(r"\n[ \t]*\n(?=[ \t]*\n)", "\n", page)
        if lang == "en":
            page = re.sub(r'(src|href)="(assets|media)/', r'\1="../\2/', page)
        if "{{" in page:
            sys.exit(f"Unresolved token in {fname}: {re.findall(r'{{.*?}}', page)}")
        (target / fname).write_text(page, encoding="utf-8", newline="\n")
        names.append(fname)
    return names


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC / "assets", OUT / "assets")
    shutil.copytree(ROOT / "admin", OUT / "admin")
    shutil.copy(ROOT / "_headers", OUT / "_headers")  # Cloudflare Pages: keep /admin out of search engines
    (OUT / "robots.txt").write_text("User-agent: *\nDisallow: /admin/\n", encoding="utf-8")
    nl = build("nl", OUT)
    en = build("en", OUT / "en")
    print(f"Built {len(nl)} Dutch and {len(en)} English pages into {OUT.name}/")
    for w in dict.fromkeys(warnings):
        print("WARNING:", w)


if __name__ == "__main__":
    main()
