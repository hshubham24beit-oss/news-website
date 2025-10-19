# news/urls.py
from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.home, name='home'),
    path('world/', views.world, name='world'),
    # category pages for country cards (id-based)
    path('category/<int:category_id>/', views.category_news, name='category_news'),
    # news detail
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),
]
