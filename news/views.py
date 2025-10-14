# news/views.py
from django.shortcuts import render, get_object_or_404
from .models import News, Category

def home(request):
    # all news ordered newest first
    all_news = News.objects.order_by('-created_at')

    # hero article: the newest one (None if no articles)
    hero = all_news.first()

    # latest four (excluding hero if it exists)
    if hero:
        latest_four = list(all_news[1:5])   # items 2..5 (max 4)
    else:
        latest_four = list(all_news[:4])    # first 4 if no hero

    # Example trending list (you can change criteria)
    trending_list = News.objects.order_by('-created_at')[:5]

    return render(request, 'news/home.html', {
        'hero': hero,
        'latest_four': latest_four,
        'trending_list': trending_list,
        'news_list': all_news,       # optional for other sections
    })

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
