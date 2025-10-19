# news/views.py
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import FieldError
from .models import News, Category


def home(request):
    """
    Site home: shows global hero, latest four and trending.
    """
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
    """
    World category page: try slug 'world' then fallback to name 'World'.
    """
    # Robust lookup: try slug then name
    try:
        try:
            category = Category.objects.get(slug__iexact='world')
        except (Category.DoesNotExist, FieldError):
            category = Category.objects.get(name__iexact='World')
    except Category.DoesNotExist:
        # If still not found, 404
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
    Generic category page by id.
    Behavior:
      - Display header/nav/footer
      - Show the most recent News in that category as a hero (image + title + content)
      - Optionally show other articles in that category below (passed in context)
    """
    category = get_object_or_404(Category, id=category_id)
    news_qs = News.objects.filter(category=category).order_by('-created_at')

    # Choose latest article in that category to show prominently
    hero_article = news_qs.first() if news_qs.exists() else None
    other_articles = news_qs[1:10] if news_qs.exists() else []

    context = {
        'category': category,
        'hero_article': hero_article,
        'other_articles': other_articles,
    }
    # Render a dedicated category template
    return render(request, 'news/countries-category.html', context)


def news_detail(request, news_id):
    """
    News detail page (single article).
    """
    news = get_object_or_404(News, id=news_id)
    return render(request, 'news/detail.html', {'news': news})
