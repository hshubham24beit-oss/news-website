# news/views.py
from django.shortcuts import render, get_object_or_404
from .models import News, Category

def home(request):
    news_list = News.objects.order_by('-created_at')
    return render(request, 'news/home.html', {'news_list': news_list})

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
