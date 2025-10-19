# news/views.py
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import FieldError
from .models import News, Category

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
        except (Category.DoesNotExist, FieldError):
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
    """
    Generic category page by id used for home/category links.
    Uses distinct context keys: category, category_hero, category_articles
    Renders templates/news/countries-category.html (you already have this file).
    """
    print("DEBUG: category_news called for id=", category_id, "path=", request.path)

    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by('-created_at')

    category_hero = news_qs.first() if news_qs.exists() else None
    category_articles = news_qs[1:20] if news_qs.exists() else []

    context = {
        'category': category,
        'category_hero': category_hero,
        'category_articles': category_articles,
    }
    # render the template you already have
    return render(request, 'news/detail.html', context)

# news/views.py

from django.shortcuts import render, get_object_or_404

def _attach_teaser_to_queryset(qs):
    """
    Ensure every News instance in qs has a safe .teaser attribute we can render
    in templates without risking VariableDoesNotExist.
    """
    for obj in qs:
        # prefer excerpt, then summary, then empty string
        teaser = ''
        # use getattr with defaults to avoid attribute errors
        teaser = getattr(obj, 'excerpt', None) or getattr(obj, 'summary', None) or ''
        # set attribute on the instance (harmless and handy in template)
        setattr(obj, 'teaser', teaser)
    return qs


def country_category(request, category_id):
    """
    Country/category view.
    Priority:
      1. Use hero_title & hero_image passed via GET (from World page).
      2. Otherwise, fall back to latest article in that category.
    Also attach .teaser to all article objects.
    """
    print("DEBUG country_category:", request.path, request.GET.dict())

    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by('-created_at')

    # GET params from world page (preferred)
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

    # Prepare other_articles queryset/list and attach teaser safely
    if hero_article:
        other_qs = news_qs.exclude(id=hero_article.id)[:20]
    else:
        other_qs = news_qs[:20]

    other_qs = list(other_qs)  # evaluate
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
