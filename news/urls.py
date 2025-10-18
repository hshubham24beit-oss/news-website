# news/urls.py
from django.urls import path
from . import views

app_name = 'news'   # <-- important: enables 'news:...' namespacing

urlpatterns = [
    path('', views.home, name='home'),
    path('world/', views.world, name='world'),
    path('category/<int:category_id>/', views.category_news, name='category_news'),
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),
]
