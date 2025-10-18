# news/views.py
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import FieldError
from .models import News, Category
from django.templatetags.static import static


def home(request):
    """
    Home page: shows site-wide latest news and hero article.
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
    World category page.
    Tries to fetch Category by slug 'world' first; if that field doesn't exist
    or the object isn't found, falls back to name='World'.
    """
    # Attempt slug lookup but handle cases where Category has no slug field
    try:
        try:
            category = Category.objects.get(slug__iexact='world')
        except (Category.DoesNotExist, FieldError):
            # Either slug field doesn't exist (FieldError) or no slug matched (DoesNotExist)
            category = Category.objects.get(name__iexact='World')
    except Category.DoesNotExist:
        # No Category with slug 'world' or name 'World' -> 404
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
    Generic category page by ID. Builds the same hero/latest/trending context as home.
    """
    category = get_object_or_404(Category, id=category_id)
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
    return render(request, 'news/home.html', context)


def news_detail(request, news_id):
    """
    News detail page.
    """
    news = get_object_or_404(News, id=news_id)
    return render(request, 'news/detail.html', {'news': news})


