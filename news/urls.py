# news/urls.py
from django.urls import path
from . import views

app_name = 'news'

urlpatterns = [
    path('', views.home, name='home'),
    path('world/', views.world, name='world'),

    # country/category route: optional news_id for hero coming from world page
    path('world/category/<int:category_id>/', views.country_category, name='countries_category'),
    path('world/category/<int:category_id>/news/<int:news_id>/', views.country_category, name='countries_category_with_news'),

    path('category/<int:category_id>/', views.category_news, name='category_news'),
    path('news/<int:news_id>/', views.news_detail, name='news_detail'),
    path('politics/', views.politics, name='politics'),
    path("politics/<int:pk>/", views.politics_category, name="politics_category"),
    

]
