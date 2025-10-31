# news/views.py
import json
import logging
import hashlib
import re
import html
from xml.etree import ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import timedelta

import requests
from bs4 import BeautifulSoup  # ensure beautifulsoup4 is installed

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST, require_GET
from django.utils import timezone

from .models import News, Category

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Cache TTL in seconds (5 minutes)
CACHE_TTL = 60 * 5
WORLDNEWS_CACHE_KEY = "worldnews_top_hero_v1"
HERO_API_CACHE_KEY = "news:hero_api_v1"


def clear_worldnews_cache():
    """Helper to delete cached worldnews hero."""
    try:
        cache.delete(WORLDNEWS_CACHE_KEY)
        cache.delete(HERO_API_CACHE_KEY)
        logger.info("Cleared cache keys: %s, %s", WORLDNEWS_CACHE_KEY, HERO_API_CACHE_KEY)
    except Exception as e:
        logger.exception("Failed to clear cache: %s", e)


def _make_external_id(url: str) -> str:
    """Return a short stable id for an external URL."""
    if not url:
        url = "no-url"
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


def _cache_external_article(hero: dict):
    """
    Given a normalized hero dict (external=True), create external_id, internal_url,
    and store full article in cache under external_article:{external_id}.
    """
    if not hero or not isinstance(hero, dict) or not hero.get("external"):
        return hero

    external_url = hero.get("url") or (hero.get("raw") and hero["raw"].get("link")) or hero.get("title", "")
    external_id = _make_external_id(external_url)
    hero["external_id"] = external_id

    try:
        hero["internal_url"] = reverse("news:external_detail", args=[external_id])
    except Exception:
        hero["internal_url"] = f"/news/external/{external_id}/"

    cache_key = f"external_article:{external_id}"
    cache_data = {
        "article": hero,
        "fetched_at": timezone.now().isoformat(),
        "source_url": external_url,
    }
    try:
        cache.set(cache_key, cache_data, timeout=CACHE_TTL)
        logger.info("Cached external article under %s", cache_key)
    except Exception:
        logger.exception("Failed to cache external article %s", cache_key)

    return hero


def fetch_external_hero(timeout=6):
    """
    Try WorldNews API first (header 'x-api-key' then 'api-key' param).
    If that fails (non-200, auth issue, network), fall back to public RSS (BBC top stories).
    Returns a normalized hero dict or None. If external, the hero will include:
      - external_id (short sha1)
      - internal_url (link to local detail view)
    """
    cached = cache.get(WORLDNEWS_CACHE_KEY)
    if cached:
        logger.debug("Using cached external hero")
        return cached

    # 1) Try WorldNews (header first)
    world_url = getattr(settings, "WORLDNEWS_API_URL", "https://api.worldnewsapi.com/top-news")
    api_key = getattr(settings, "WORLDNEWS_API_KEY", None) or getattr(settings, "WORLD_NEWS_API_KEY", None)
    if not api_key:
        api_key = "8ea67e79888a431fbdcfb1c270aa04bc"  # dev fallback; don't commit real keys

    try:
        headers = {"x-api-key": api_key}
        params = {"language": "en"}
        logger.debug("Attempting worldnews header auth request")
        resp = requests.get(world_url, headers=headers, params=params, timeout=timeout)
        logger.debug("worldnews status (header): %s", getattr(resp, "status_code", None))
        if resp.status_code != 200:
            logger.debug("Header attempt failed, trying query param api-key")
            resp = requests.get(world_url, params={"api-key": api_key, "language": "en"}, timeout=timeout)
            logger.debug("worldnews status (param): %s", getattr(resp, "status_code", None))

        if resp is not None and resp.status_code == 200:
            jw = resp.json()
            first_article = None
            if isinstance(jw, dict) and "top_news" in jw and isinstance(jw["top_news"], list) and jw["top_news"]:
                first_cluster = jw["top_news"][0]
                if isinstance(first_cluster, dict) and "news" in first_cluster and isinstance(first_cluster["news"], list) and first_cluster["news"]:
                    first_article = first_cluster["news"][0]
            if not first_article:
                if isinstance(jw, dict):
                    for k in ("articles", "data", "results", "news", "items"):
                        if k in jw and isinstance(jw[k], list) and jw[k]:
                            first_article = jw[k][0]
                            break
                    if not first_article:
                        for v in jw.values():
                            if isinstance(v, list) and v and isinstance(v[0], dict):
                                first_article = v[0]
                                break
                elif isinstance(jw, list) and jw:
                    first_article = jw[0]

            if first_article and isinstance(first_article, dict):
                title = first_article.get("title") or first_article.get("headline") or first_article.get("name") or first_article.get("summary") or first_article.get("description")
                url = first_article.get("url") or first_article.get("link") or first_article.get("news_url") or first_article.get("source_url") or "#"
                image_url = first_article.get("image") or first_article.get("image_url") or first_article.get("thumbnail") or ""
                published_at = first_article.get("publish_date") or first_article.get("publishedAt") or first_article.get("published_at")
                source_name = (first_article.get("source") and (first_article["source"].get("name") or first_article["source"])) or first_article.get("source_name")
                content = first_article.get("content") or first_article.get("description") or first_article.get("summary") or ""
                hero = {
                    "title": title or "Top news",
                    "url": url,
                    "image_url": image_url or "",
                    "published_at": published_at,
                    "source_name": source_name,
                    "external": True,
                    "raw": first_article,
                    "content": content,
                }
                hero = _cache_external_article(hero)
                cache.set(WORLDNEWS_CACHE_KEY, hero, timeout=CACHE_TTL)
                logger.info("Using WorldNews API result as hero")
                return hero
            else:
                logger.warning("WorldNews responded 200 but no usable first article found; falling back to RSS")
        else:
            body = getattr(resp, "text", "<no-body>") if resp is not None else "<no-response>"
            logger.warning("WorldNews non-200 or no response; status=%s body=%s", getattr(resp, "status_code", None), (body or "")[:1000])

    except Exception as exc:
        logger.exception("Error calling WorldNews API: %s", exc)

    # 2) Fallback: fetch a public RSS (BBC Top Stories)
    try:
        rss_url = "http://feeds.bbci.co.uk/news/rss.xml"
        logger.debug("Fetching RSS fallback from %s", rss_url)
        r = requests.get(rss_url, timeout=6)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        channel = root.find("channel")
        first_item = None
        if channel is not None:
            first_item = channel.find("item")
        if first_item is None:
            items = root.findall(".//item")
            first_item = items[0] if items else None

        if first_item is not None:
            def get_text(elem, tag):
                t = elem.find(tag)
                return t.text.strip() if t is not None and t.text else None

            title = get_text(first_item, "title") or "Top story"
            link = get_text(first_item, "link") or "#"
            image_url = ""
            enclosure = first_item.find("enclosure")
            if enclosure is not None and "url" in enclosure.attrib:
                image_url = enclosure.attrib.get("url")
            else:
                thumb = first_item.find("{http://search.yahoo.com/mrss/}thumbnail")
                if thumb is not None and "url" in thumb.attrib:
                    image_url = thumb.attrib.get("url")
                else:
                    media_content = first_item.find("{http://search.yahoo.com/mrss/}content")
                    if media_content is not None and "url" in media_content.attrib:
                        image_url = media_content.attrib.get("url")

            content = get_text(first_item, "description") or ""
            hero = {
                "title": title,
                "url": link,
                "image_url": image_url or "",
                "published_at": get_text(first_item, "pubDate"),
                "source_name": "BBC News (RSS)",
                "external": True,
                "raw": ET.tostring(first_item, encoding="unicode"),
                "content": content,
            }
            hero = _cache_external_article(hero)
            cache.set(WORLDNEWS_CACHE_KEY, hero, timeout=CACHE_TTL)
            logger.info("Using RSS fallback (BBC) as hero")
            return hero
        else:
            logger.warning("RSS fallback: no <item> found in feed")
    except Exception as exc:
        logger.exception("RSS fallback failed: %s", exc)

    logger.warning("No external hero found (WorldNews failed, RSS fallback failed).")
    return None


@require_GET
def hero_api(request):
    """
    Return the hero article as JSON.
    Behavior:
      - Uses cached HERO_API_CACHE_KEY if present.
      - Honors USE_EXTERNAL_HERO setting similar to home() decision logic.
      - Normalizes both external dict and local News model into a consistent JSON shape.
    """
    cached = cache.get(HERO_API_CACHE_KEY)
    if cached:
        logger.debug("hero_api: returning cached hero response")
        return JsonResponse(cached)

    mode = getattr(settings, "USE_EXTERNAL_HERO", True)
    hero_obj = None

    # Determine hero selection logic consistent with home()
    if mode is True or mode == "force":
        external_hero = fetch_external_hero()
        if external_hero:
            hero_obj = external_hero
            logger.debug("hero_api: using external hero (mode=%s)", mode)
        else:
            hero_obj = News.objects.order_by("-created_at").first()
            logger.debug("hero_api: external missing, falling back to DB")
    elif mode == "fallback":
        hero_obj = News.objects.order_by("-created_at").first()
        if not hero_obj:
            hero_obj = fetch_external_hero()
    else:
        hero_obj = News.objects.order_by("-created_at").first()

    if not hero_obj:
        logger.debug("hero_api: no hero available")
        return JsonResponse({}, status=204, safe=False)

    # Normalize response
    if isinstance(hero_obj, dict) and hero_obj.get("external"):
        # ensure cached, get internal_url/external_id set
        hero = _cache_external_article(hero_obj)
        response = {
            "external": True,
            "external_id": hero.get("external_id"),
            "title": hero.get("title"),
            "url": hero.get("url"),
            "internal_url": request.build_absolute_uri(hero.get("internal_url")) if hero.get("internal_url") else None,
            "image_url": hero.get("image_url") or None,
            "published_at": hero.get("published_at"),
            "source_name": hero.get("source_name"),
            "content": hero.get("content"),
            "raw": hero.get("raw"),
        }
    else:
        # assume a News model instance
        news = hero_obj
        try:
            image_url = request.build_absolute_uri(news.image.url) if getattr(news, "image", None) and getattr(news.image, "url", None) else None
        except Exception:
            image_url = None
        try:
            internal = request.build_absolute_uri(reverse("news:news_detail", args=[news.id]))
        except Exception:
            internal = request.build_absolute_uri(f"/news/{getattr(news, 'id', '')}/")
        response = {
            "external": False,
            "id": getattr(news, "id", None),
            "title": getattr(news, "title", ""),
            "internal_url": internal,
            "image_url": image_url,
            "published_at": getattr(news, "created_at").isoformat() if getattr(news, "created_at", None) else None,
            "category": getattr(getattr(news, "category", None), "name", None),
            "excerpt": getattr(news, "excerpt", "") or getattr(news, "summary", "") or "",
        }

    # Cache normalized response for a short period to reduce load
    try:
        cache.set(HERO_API_CACHE_KEY, response, timeout=CACHE_TTL)
    except Exception:
        logger.exception("hero_api: failed to cache response")

    return JsonResponse(response)


@ensure_csrf_cookie
def home(request):
    """
    Home page:
      - mode = settings.USE_EXTERNAL_HERO:
          True or "force" -> prefer external and override DB when available
          "fallback" -> prefer DB, use external only if DB missing
          False -> DB only
    """
    news_qs = News.objects.order_by("-created_at")

    mode = getattr(settings, "USE_EXTERNAL_HERO", True)
    logger.debug("USE_EXTERNAL_HERO mode=%s", mode)

    hero = None
    if mode is True or mode == "force":
        external_hero = fetch_external_hero()
        if external_hero:
            logger.debug("Using external hero (mode=%s)", mode)
            hero = external_hero
        else:
            logger.debug("External hero not available; using DB hero")
            hero = news_qs.first() if news_qs.exists() else None
    elif mode == "fallback":
        hero = news_qs.first() if news_qs.exists() else None
        if not hero:
            hero = fetch_external_hero()
    else:
        hero = news_qs.first() if news_qs.exists() else None

    if hero and hasattr(hero, "id"):
        latest_four = news_qs.exclude(id=hero.id)[:4]
    else:
        latest_four = news_qs[:4]

    trending_list = news_qs[:5]

    context = {
        "hero": hero,
        "latest_four": latest_four,
        "trending_list": trending_list,
        "news_list": news_qs,
        "selected_category": None,
    }
    return render(request, "news/home.html", context)


def _strip_tags_and_unescape(html_text: str) -> str:
    """Strip tags, preserve basic paragraphs/linebreaks, unescape HTML entities."""
    if not html_text:
        return ""
    # remove script/style
    s = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html_text)
    # replace <br> and closing </p> with newlines
    s = re.sub(r"(?i)<br\s*/?>", "\n", s)
    s = re.sub(r"(?i)</p\s*>", "\n\n", s)
    # remove remaining tags
    text = re.sub(r"<[^>]+>", "", s)
    # unescape HTML entities
    text = html.unescape(text)
    # collapse repeated spaces but preserve line breaks
    text = re.sub(r"[ \t]{2,}", " ", text)
    lines = [ln.strip() for ln in text.splitlines()]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _extract_from_raw(raw):
    """Extract plain text from raw dict or RSS/XML string."""
    if not raw:
        return ""
    if isinstance(raw, dict):
        for key in ("_extracted_text", "content", "description", "summary", "excerpt", "body", "text"):
            val = raw.get(key)
            if val and isinstance(val, str) and val.strip():
                return _strip_tags_and_unescape(val)
        if "article" in raw and isinstance(raw["article"], dict):
            for key in ("content", "description", "summary"):
                val = raw["article"].get(key)
                if val and isinstance(val, str) and val.strip():
                    return _strip_tags_and_unescape(val)
        return ""
    if isinstance(raw, str) and raw.strip().startswith("<"):
        try:
            node = ET.fromstring(raw)
            desc = node.find("description")
            if desc is not None and desc.text and desc.text.strip():
                return _strip_tags_and_unescape(desc.text)
            cc = node.find("{http://purl.org/rss/1.0/modules/content/}encoded")
            if cc is not None and cc.text and cc.text.strip():
                return _strip_tags_and_unescape(cc.text)
            paragraphs = [p.text for p in node.findall(".//p") if p.text]
            if paragraphs:
                return _strip_tags_and_unescape("\n\n".join(paragraphs))
        except Exception:
            return _strip_tags_and_unescape(raw)
    return _strip_tags_and_unescape(str(raw))


def _extract_text_with_bs4(html_body: str, max_paragraphs: int = 12) -> str:
    """
    Use BeautifulSoup to extract the main article text.
    Heuristic:
      1. Look for <article>, <main>, role="main".
      2. If none, score <div> blocks by text length and take the largest.
      3. Return joined paragraphs (up to max_paragraphs), cleaned.
    """
    if not html_body:
        return ""

    try:
        soup = BeautifulSoup(html_body, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(html_body, "html.parser")
        except Exception:
            return ""  # soup failed

    # 1) article/main/role=main
    candidates = []
    article_tag = soup.find("article")
    if article_tag:
        candidates.append(article_tag)
    main_tag = soup.find("main")
    if main_tag:
        candidates.append(main_tag)
    role_main = soup.find(attrs={"role": "main"})
    if role_main:
        candidates.append(role_main)

    # If we have candidates, pick the one with most text
    best = None
    best_len = 0
    for c in candidates:
        text = c.get_text(separator="\n\n", strip=True)
        l = len(text)
        if l > best_len:
            best = c
            best_len = l

    # 2) Otherwise, find largest <div> by text length
    if best is None:
        divs = soup.find_all("div")
        for d in divs:
            text = d.get_text(separator="\n\n", strip=True)
            # ignore tiny divs
            if len(text) < 120:
                continue
            l = len(text)
            if l > best_len:
                best = d
                best_len = l

    # 3) Fallback to body paragraphs
    if best is None:
        paragraphs = soup.find_all("p")
        if not paragraphs:
            return ""
        text_nodes = []
        for p in paragraphs[:max_paragraphs]:
            p_text = p.get_text(strip=True)
            if p_text:
                text_nodes.append(p_text)
        return "\n\n".join(text_nodes) if text_nodes else ""

    # Extract paragraphs from best
    paras = best.find_all("p")
    if paras:
        collected = []
        for p in paras[:max_paragraphs]:
            t = p.get_text(strip=True)
            if t:
                collected.append(t)
        if collected:
            return "\n\n".join(collected)

    # If no paragraphs, fallback to the full text of the block, trimmed
    text = best.get_text(separator="\n\n", strip=True)
    # limit to first N lines / paragraphs
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    # join up to max_paragraphs blocks approximated by blank-line separation
    joined = "\n\n".join(lines[: max_paragraphs * 3])  # keep more lines if paragraphs missing
    return joined


# ----- BBC-focused extractor helper -----
def _extract_text_from_bbc(html_body: str, max_paragraphs: int = 30) -> str:
    """
    BBC-optimized extractor:
      - collects <div data-component="text-block"> paragraphs first
      - then looks for common BBC paragraph class patterns (ssrcss-*)
      - falls back to <article>, <main>, or largest <div> heuristic
    Returns plain text (paragraphs joined by blank line) or empty string.
    """
    if not html_body:
        return ""

    try:
        soup = BeautifulSoup(html_body, "lxml")
    except Exception:
        soup = BeautifulSoup(html_body, "html.parser")

    # 1) BBC's text-blocks
    text_nodes = []
    for block in soup.select('div[data-component="text-block"]'):
        # paragraphs inside block
        for p in block.find_all("p"):
            t = p.get_text(strip=True)
            if t:
                text_nodes.append(t)
        if len(text_nodes) >= max_paragraphs:
            break
    if text_nodes:
        return "\n\n".join(text_nodes[:max_paragraphs])

    # 2) BBC uses class names with 'ssrcss' or paragraph-like classes
    candidates = []
    for p in soup.find_all("p"):
        cls = " ".join(p.get("class") or [])
        if "ssrcss" in cls or "Paragraph" in cls or "paragraph" in cls or cls.startswith("gel-"):
            t = p.get_text(strip=True)
            if t:
                candidates.append(t)
            if len(candidates) >= max_paragraphs:
                break
    if candidates:
        return "\n\n".join(candidates[:max_paragraphs])

    # 3) Try article/main/role=main
    for sel in ("article", "main", '[role="main"]'):
        el = soup.select_one(sel)
        if el:
            paras = [p.get_text(strip=True) for p in el.find_all("p") if p.get_text(strip=True)]
            if paras:
                return "\n\n".join(paras[:max_paragraphs])

    # 4) Largest div heuristic
    best = None
    best_len = 0
    for d in soup.find_all("div"):
        txt = d.get_text(separator="\n\n", strip=True)
        if len(txt) < 120:
            continue
        l = len(txt)
        if l > best_len:
            best = d
            best_len = l
    if best:
        paras = [p.get_text(strip=True) for p in best.find_all("p") if p.get_text(strip=True)]
        if paras:
            return "\n\n".join(paras[:max_paragraphs])
        # fallback to trimmed text
        text = best.get_text(separator="\n\n", strip=True)
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if lines:
            return "\n\n".join(lines[: max_paragraphs * 2])

    return ""


# ----- replace external_detail with this BBC-aware version -----
def external_detail(request, external_id):
    """
    Show external article using cached external_article:{external_id}.
    If `_extracted_text` missing or too short, fetch source and use BBC-tuned extractor,
    then cache the result under article['_extracted_text'].
    Renders your existing news/detail.html with a synthetic news object.
    """
    cache_key = f"external_article:{external_id}"
    cached = cache.get(cache_key)
    if not cached or not isinstance(cached, dict):
        logger.warning("External article cache miss for %s", cache_key)
        return redirect("/")

    article = cached.get("article") or {}
    source_url = cached.get("source_url") or article.get("url") or "#"

    # Prefer already extracted text
    extracted = ""
    if isinstance(article, dict):
        extracted = article.get("_extracted_text") or ""

    # If none or very short, try content/raw fields
    if not extracted or len(extracted.strip()) < 80:
        # try article['content'] or rss raw extraction
        if article.get("content"):
            extracted_candidate = _strip_tags_and_unescape(article.get("content"))
            if len(extracted_candidate) > len(extracted):
                extracted = extracted_candidate

        if not extracted or len(extracted.strip()) < 80:
            extracted_candidate = _extract_from_raw(article.get("raw"))
            if len(extracted_candidate) > len(extracted):
                extracted = extracted_candidate

    # If still short/empty, fetch source and run BBC-focused extractor, then fallback heuristics
    need_fetch = not extracted or len(extracted.strip()) < 120
    if need_fetch and source_url and source_url.startswith("http"):
        try:
            logger.debug("external_detail: fetching source_url=%s", source_url)
            resp = requests.get(source_url, timeout=12, headers={"User-Agent": "Mozilla/5.0 (compatible)"})
            if resp.status_code == 200 and resp.text:
                # 1) quick meta description
                m = re.search(r'<meta\s+property=["\']og:description["\']\s+content=["\']([^"\']+)["\']', resp.text, flags=re.I)
                if not m:
                    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)["\']', resp.text, flags=re.I)
                if m:
                    meta_desc = _strip_tags_and_unescape(html.unescape(m.group(1)))
                    if len(meta_desc) > len(extracted):
                        extracted = meta_desc

                # 2) BBC tailored extractor
                bbc_text = _extract_text_from_bbc(resp.text, max_paragraphs=40)
                if bbc_text and len(bbc_text) > len(extracted):
                    extracted = bbc_text

                # 3) general bs4 heuristic as fallback (reuse previous function if present)
                if (not extracted or len(extracted) < 120):
                    try:
                        gs = _extract_text_with_bs4(resp.text, max_paragraphs=30)
                        if gs and len(gs) > len(extracted):
                            extracted = gs
                    except Exception:
                        pass

                # 4) regex paragraphs fallback
                if (not extracted or len(extracted) < 120):
                    paragraphs = re.findall(r'(?is)<p[^>]*>(.*?)</p>', resp.text)
                    if paragraphs:
                        sample = "\n\n".join([_strip_tags_and_unescape(p) for p in paragraphs[:12]])
                        if len(sample) > len(extracted):
                            extracted = sample
        except Exception as exc:
            logger.exception("external_detail: failed to fetch/parse source_url %s: %s", source_url, exc)

    # Last fallback: title / short message
    if not extracted or len(extracted.strip()) < 40:
        extracted = article.get("title") or article.get("content") or "Full article not available. Read on source."

    # Save extracted text back into cache under article['_extracted_text']
    try:
        if isinstance(cached.get("article"), dict):
            cached["article"]["_extracted_text"] = extracted
            cache.set(cache_key, cached, timeout=CACHE_TTL)
    except Exception:
        logger.exception("Failed to cache extracted text for %s", cache_key)

    # parse created_at for detail template date filter
    created_at_raw = article.get("published_at") or article.get("published") or cached.get("fetched_at")
    created_at_dt = None
    if created_at_raw:
        try:
            created_at_dt = parsedate_to_datetime(created_at_raw)
            if created_at_dt.tzinfo is None:
                created_at_dt = timezone.make_aware(created_at_dt, timezone.get_default_timezone())
        except Exception:
            created_at_dt = timezone.now()
    else:
        created_at_dt = timezone.now()

    # Build synthetic news object for template
    class _Img:
        def __init__(self, url):
            self.url = url

    class _Cat:
        def __init__(self, name):
            self.name = name

    class _SyntheticNews:
        def __init__(self, title, image_url, created_at, content, category_name, source_url):
            self.id = None
            self.title = title
            self.image = _Img(image_url) if image_url else None
            self.created_at = created_at
            self.content = content
            self.excerpt = content
            self.summary = content
            self.category = _Cat(category_name or "External")
            self.source_url = source_url

        def get_absolute_url(self):
            return self.source_url

    news_obj = _SyntheticNews(
        title=article.get("title") or article.get("headline") or "External story",
        image_url=article.get("image_url") or article.get("thumbnail") or "",
        created_at=created_at_dt,
        content=extracted,
        category_name=article.get("source_name") or "External",
        source_url=source_url,
    )

    logger.debug("external_detail: external_id=%s extracted_len=%d source=%s", external_id, len(extracted or ""), source_url)
    return render(request, "news/detail.html", {"news": news_obj})


def world(request):
    try:
        try:
            category = Category.objects.get(slug__iexact="world")
        except (Category.DoesNotExist, Exception):
            category = Category.objects.get(name__iexact="World")
    except Category.DoesNotExist:
        category = get_object_or_404(Category, name__iexact="World")

    news_qs = News.objects.filter(category=category).order_by("-created_at")
    hero = news_qs.first() if news_qs.exists() else None
    latest_four = news_qs.exclude(id=hero.id)[:4] if hero else news_qs[:4]
    trending_list = news_qs[:5]

    context = {
        "hero": hero,
        "latest_four": latest_four,
        "trending_list": trending_list,
        "news_list": news_qs,
        "selected_category": category,
    }
    return render(request, "news/world.html", context)


def category_news(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by("-created_at")

    category_hero = news_qs.first() if news_qs.exists() else None
    category_articles = news_qs[1:20] if news_qs.exists() else []

    context = {
        "category": category,
        "category_hero": category_hero,
        "category_articles": category_articles,
    }
    return render(request, "news/detail.html", context)


def _attach_teaser_to_queryset(qs):
    for obj in qs:
        teaser = getattr(obj, "excerpt", None) or getattr(obj, "summary", None) or ""
        setattr(obj, "teaser", teaser)
    return qs


def country_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by("-created_at")

    hero_title = request.GET.get("hero_title")
    hero_image = request.GET.get("hero_image")

    hero_article = None
    if not hero_title or not hero_image:
        hero_article = news_qs.first() if news_qs.exists() else None
        if hero_article:
            hero_title = hero_article.title
            try:
                hero_image = hero_article.image.url
            except Exception:
                hero_image = None

    if hero_article:
        other_qs = news_qs.exclude(id=hero_article.id)[:20]
    else:
        other_qs = news_qs[:20]

    other_qs = list(other_qs)
    _attach_teaser_to_queryset(other_qs)

    context = {
        "category": category,
        "hero_title": hero_title,
        "hero_image": hero_image,
        "hero_article": hero_article,
        "other_articles": other_qs,
    }
    return render(request, "news/countries-category.html", context)


def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    return render(request, "news/detail.html", {"news": news})


def politics(request):
    return render(request, "news/politics.html")


def politics_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    hero_title = request.GET.get("hero_title")
    hero_image = request.GET.get("hero_image")
    hero_article = None

    context = {
        "category": category,
        "hero_title": hero_title,
        "hero_image": hero_image,
        "hero_article": hero_article,
    }
    return render(request, "news/politics_category.html", context)


def tech(request):
    return render(request, "news/tech.html")


def tech_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    hero_title = request.GET.get("hero_title", category.name)
    hero_image = request.GET.get("hero_image", "")
    return render(
        request,
        "news/tech_category.html",
        {
            "category": category,
            "hero_title": hero_title,
            "hero_image": hero_image,
        },
    )


@require_POST
def weather_proxy(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
        lat = float(data.get("lat"))
        lon = float(data.get("lon"))
    except Exception:
        return HttpResponseBadRequest("Invalid payload")

    cache_key = f"weather:{lat:.4f}:{lon:.4f}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached)

    try:
        if getattr(settings, "USE_OPEN_METEO", False):
            url = (
                f"https://api.open-meteo.com/v1/forecast?"
                f"latitude={lat}&longitude={lon}&current_weather=true&timezone=auto"
            )
            resp = requests.get(url, timeout=6)
            resp.raise_for_status()
            jw = resp.json()
            cw = jw.get("current_weather", {})
            result = {
                "temp": cw.get("temperature"),
                "condition": "Unknown",
                "icon": None,
                "humidity": None,
                "wind_kph": cw.get("windspeed"),
                "sunrise": None,
                "sunset": None,
                "location_name": jw.get("timezone", ""),
                "raw": jw,
            }
        else:
            appid = getattr(settings, "OPENWEATHERMAP_API_KEY", None)
            if not appid:
                return HttpResponseServerError("OPENWEATHERMAP_API_KEY not configured on server.")
            url = (
                "https://api.openweathermap.org/data/2.5/weather"
                f"?lat={lat}&lon={lon}&appid={appid}&units=metric"
            )
            resp = requests.get(url, timeout=6)
            resp.raise_for_status()
            jw = resp.json()

            weather = jw.get("weather", [{}])[0]
            main = jw.get("main", {})
            wind = jw.get("wind", {})
            sys = jw.get("sys", {})

            result = {
                "temp": main.get("temp"),
                "condition": weather.get("main") or weather.get("description"),
                "description": weather.get("description"),
                "icon": (
                    f"https://openweathermap.org/img/wn/{weather.get('icon')}@2x.png"
                    if weather.get("icon")
                    else None
                ),
                "humidity": main.get("humidity"),
                "wind_kph": wind.get("speed"),
                "sunrise": sys.get("sunrise"),
                "sunset": sys.get("sunset"),
                "location_name": f"{jw.get('name','')}, {jw.get('sys',{}).get('country','')}",
                "raw": jw,
            }
    except requests.RequestException as exc:
        return HttpResponseServerError(f"Weather provider error: {exc}")

    cache.set(cache_key, result, CACHE_TTL)
    return JsonResponse(result)


def sports(request):
    context = {
        "active_category": "sports",
    }
    return render(request, "news/sports.html", context)


def sports_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    hero_title = request.GET.get("hero_title", category.name)
    hero_image = request.GET.get("hero_image", "")
    return render(
        request,
        "news/sports_category.html",
        {"category": category, "hero_title": hero_title, "hero_image": hero_image},
    )


def entertainment(request):
    return render(request, "news/entertainment.html")


def entertainment_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    hero_title = request.GET.get("hero_title", category.name)
    hero_image = request.GET.get("hero_image", "")
    return render(
        request,
        "news/entertainment_category.html",
        {"category": category, "hero_title": hero_title, "hero_image": hero_image},
    )
