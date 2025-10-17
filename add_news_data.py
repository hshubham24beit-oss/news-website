import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from news.models import Category, News
from django.utils import timezone

# ensure categories exist & map names -> objects
names = ['World', 'Politics', 'Tech', 'Sports', 'Entertainment']
for n in names:
    Category.objects.get_or_create(name=n)
cats = {c.name: c for c in Category.objects.all()}

# define the content to write (ID order 1..5)
data = [
    {
        'title': "Breakthrough Cancer Therapy Shows Promising Results",
        'content': "A new therapy developed by researchers demonstrates significant tumor reduction in early clinical trials, offering hope to millions around the world.",
        'category': cats['World']
    },
    {
        'title': "Elections 2025: Key Takeaways from Last Night",
        'content': "Voters turned out in record numbers as major upsets reshaped the political landscape. Analysts say the results will have long-term implications.",
        'category': cats['Politics']
    },
    {
        'title': "New Phone Launch: What's Different This Year",
        'content': "The latest model introduces a flexible display and longer battery life, though there are debates about pricing and software.",
        'category': cats['Tech']
    },
    {
        'title': "City Wins Comeback Thriller in Final Seconds",
        'content': "In an unbelievable finish, the home team reversed a late deficit and sealed victory with a buzzer-beater. Fans celebrated into the night.",
        'category': cats['Sports']
    },
    {
        'title': "Film Festival Highlights: The Year's Best Indies",
        'content': "Critics praise a small set of independent films for bold storytelling and striking visuals; audiences responded enthusiastically.",
        'category': cats['Entertainment']
    },
]

# find five News objects (prefer existing demo ones)
news_qs = list(News.objects.order_by('id')[:5])
if len(news_qs) < 5:
    for i in range(5 - len(news_qs)):
        News.objects.create(
            title=f"Auto Demo {i+1}",
            content="Temporary",
            category=list(cats.values())[i % len(cats)],
            created_at=timezone.now()
        )
    news_qs = list(News.objects.order_by('id')[:5])

# update them
for obj, item in zip(news_qs, data):
    obj.title = item['title']
    obj.content = item['content']
    obj.category = item['category']
    obj.created_at = timezone.now()
    obj.save()

print("✅ Updated news count:", News.objects.count())
print("📰 Updated IDs:", [n.id for n in news_qs])
