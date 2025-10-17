# news/views.py
from django.shortcuts import render, get_object_or_404
from .models import News, Category

def home(request):
    # Get all news ordered by newest first
    news_qs = News.objects.order_by('-created_at')

    # Set hero as the newest (ID 5 in your case)
    hero = news_qs.first()

    # Get next 4 latest excluding hero
    latest_four = news_qs.exclude(id=hero.id)[:4] if hero else news_qs[:5]

    # Trending can just reuse the same 4 for now
    trending_list = news_qs[:5]

    context = {
        'hero': hero,
        'latest_four': latest_four,
        'trending_list': trending_list,
        'news_list': news_qs,  # fallback for older template parts
    }
    return render(request, 'news/home.html', context)
def category_news(request, category_id):
    category = get_object_or_404(Category, id=category_id)
    news_list = News.objects.filter(category=category).order_by('-created_at')
    return render(request, 'news/home.html', {
        'news_list': news_list,
        'selected_category': category
    })

def news_detail(request, news_id):
    news = get_object_or_404(News, id=news_id)
    return render(request, 'news/detail.html', {'news': news})
