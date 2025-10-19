# news/views.py
from django.shortcuts import render, get_object_or_404
from django.core.exceptions import FieldError
from django.templatetags.static import static
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
    # Try slug lookup first, fallback to name
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
    Generic category page (used by country cards). Show only header/navbar/footer
    plus a top hero area: image, title and long content. If the category has at
    least one News item we use that News as hero; otherwise we show a fallback
    static country image and default text.
    """
    category = get_object_or_404(Category, id=category_id)

    # all news in this category
    news_qs = News.objects.filter(category=category).order_by('-created_at')

    # choose hero source: first News in category if exists, else fallback
    hero_item = news_qs.first() if news_qs.exists() else None

    if hero_item:
        hero_image_url = hero_item.image.url if hero_item.image else static(f'images/countries/{category.slug}.jpg')
        hero_title = hero_item.title
        hero_content = hero_item.content
    else:
        # fallback image file should exist in static/images/countries/<slug>.jpg
        hero_image_url = static(f'images/countries/{category.slug}.jpg')
        hero_title = category.name
        hero_content = (
            f"{category.name} is one of the most important regions in world news. "
            "Stay tuned for the latest updates, top headlines, and deep insights about "
            "politics, economy, culture, and more from this region."
        )

    context = {
        'category': category,
        'hero_image_url': hero_image_url,
        'hero_title': hero_title,
        'hero_content': hero_content,
        # also provide lists in case you want to show quick links/trending in the template:
        'news_list': news_qs,
    }
    # render a dedicated category template
    return render(request, 'news/category.html', context)


def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    return render(request, 'news/detail.html', {'news': news})
