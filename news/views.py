# news/views.py
import json
import requests
from django.views.decorators.csrf import ensure_csrf_cookie

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .models import News, Category

CACHE_TTL = 60 * 5  # cache 5 minutes

@ensure_csrf_cookie
def home(request):
    ...


def home(request):
    news_qs = News.objects.order_by('-created_at')
    hero = news_qs.first() if news_qs.exists() else None
    latest_four = news_qs.exclude(id=hero.id)[:4] if hero else news_qs[:4]
    trending_list = news_qs[:5]

    context = {
        'hero': hero,
        'latest_four': latest_four,
        'trending_list': trending_list,
        'news_list': news_qs,
        'selected_category': None,
    }
    return render(request, 'news/home.html', context)


def world(request):
    try:
        try:
            category = Category.objects.get(slug__iexact='world')
        except (Category.DoesNotExist, Exception):
            category = Category.objects.get(name__iexact='World')
    except Category.DoesNotExist:
        category = get_object_or_404(Category, name__iexact='World')

    news_qs = News.objects.filter(category=category).order_by('-created_at')
    hero = news_qs.first() if news_qs.exists() else None
    latest_four = news_qs.exclude(id=hero.id)[:4] if hero else news_qs[:4]
    trending_list = news_qs[:5]

    context = {
        'hero': hero,
        'latest_four': latest_four,
        'trending_list': trending_list,
        'news_list': news_qs,
        'selected_category': category,
    }
    return render(request, 'news/world.html', context)


def category_news(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by('-created_at')

    category_hero = news_qs.first() if news_qs.exists() else None
    category_articles = news_qs[1:20] if news_qs.exists() else []

    context = {
        'category': category,
        'category_hero': category_hero,
        'category_articles': category_articles,
    }
    return render(request, 'news/detail.html', context)


def _attach_teaser_to_queryset(qs):
    for obj in qs:
        teaser = getattr(obj, 'excerpt', None) or getattr(obj, 'summary', None) or ''
        setattr(obj, 'teaser', teaser)
    return qs


def country_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by('-created_at')

    hero_title = request.GET.get('hero_title')
    hero_image = request.GET.get('hero_image')

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
        'category': category,
        'hero_title': hero_title,
        'hero_image': hero_image,
        'hero_article': hero_article,
        'other_articles': other_qs,
    }
    return render(request, 'news/countries-category.html', context)


def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    return render(request, 'news/detail.html', {'news': news})


def politics(request):
    return render(request, 'news/politics.html')


def politics_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    hero_title = request.GET.get('hero_title')
    hero_image = request.GET.get('hero_image')
    hero_article = None

    context = {
        'category': category,
        'hero_title': hero_title,
        'hero_image': hero_image,
        'hero_article': hero_article,
    }
    return render(request, 'news/politics_category.html', context)


def tech(request):
    return render(request, 'news/tech.html')


def tech_category(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    hero_title = request.GET.get('hero_title', category.name)
    hero_image = request.GET.get('hero_image', '')
    return render(request, 'news/tech_category.html', {
        'category': category,
        'hero_title': hero_title,
        'hero_image': hero_image,
    })


@require_POST
def weather_proxy(request):
    """
    Accepts JSON body: {"lat": 18.5204, "lon": 73.8567}
    Returns simplified JSON from OpenWeatherMap or Open-Meteo.
    CSRF is enforced (the front-end should send X-CSRFToken).
    """
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
            # Open-Meteo (no API key)
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
        # upstream network error / API error
        return HttpResponseServerError(f"Weather provider error: {exc}")

    cache.set(cache_key, result, CACHE_TTL)
    return JsonResponse(result)
