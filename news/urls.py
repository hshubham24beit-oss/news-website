# news/urls.py
from django.urls import path
from . import views

app_name = "news"

urlpatterns = [
    path('', views.home, name='home'),
    path('world/', views.world, name='world'),

    # country/category routes
    path('world/category/<int:category_id>/', views.country_category, name='countries_category'),
    path('world/category/<int:category_id>/news/<int:news_id>/', views.country_category, name='countries_category_with_news'),

    path('category/<int:category_id>/', views.category_news, name='category_news'),
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),

    path('politics/', views.politics, name='politics'),
    path('politics/<int:pk>/', views.politics_category, name='politics_category'),

    path('tech/', views.tech, name='tech'),
    path('tech/<int:category_id>/', views.tech_category, name='tech_category'),

    # Weather API proxy (POST)
    path('api/weather/', views.weather_proxy, name='weather_proxy'),
    path('sports/', views.sports, name='sports'),
    path('sports/', views.sports_category, name='sports_category'),

]
