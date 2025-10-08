# news/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('category/<int:category_id>/', views.category_news, name='category-news'),
    path('news/<int:news_id>/', views.news_detail, name='news-detail'),
]
