import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from news.models import Category, News

# ensure categories exist
categories = ['World', 'Politics', 'Tech', 'Sports', 'Entertainment']
for c in categories:
    Category.objects.get_or_create(name=c)
cats = {c.name: c for c in Category.objects.all()}

# new real data
data = [
    {
        "title": "Breakthrough Cancer Therapy Shows Promising Results",
        "content": "A new therapy developed by researchers demonstrates significant tumor reduction in early clinical trials, offering hope to millions around the world.",
        "category": cats['World']
    },
    {
        "title": "Elections 2025: Key Takeaways from Last Night",
        "content": "Voters turned out in record numbers as major upsets reshaped the political landscape. Analysts say the results will have long-term implications.",
        "category": cats['Politics']
    },
    {
        "title": "New Phone Launch: What's Different This Year",
        "content": "The latest model introduces a flexible display and longer battery life, though there are debates about pricing and software.",
        "category": cats['Tech']
    },
    {
        "title": "City Wins Comeback Thriller in Final Seconds",
        "content": "In an unbelievable finish, the home team reversed a late deficit and sealed victory with a buzzer-beater. Fans celebrated into the night.",
        "category": cats['Sports']
    },
    {
        "title": "Film Festival Highlights: The Year's Best Indies",
        "content": "Critics praise a small set of independent films for bold storytelling and striking visuals; audiences responded enthusiastically.",
        "category": cats['Entertainment']
    }
]

# overwrite existing news
qs = list(News.objects.order_by('id')[:5])
if len(qs) < 5:
    for i in range(5 - len(qs)):
        News.objects.create(
            title=f"Auto Demo {i+1}",
            content="Temporary",
            category=list(cats.values())[i % len(cats)],
            created_at=timezone.now()
        )
    qs = list(News.objects.order_by('id')[:5])

for obj, item in zip(qs, data):
    obj.title = item['title']
    obj.content = item['content']
    obj.category = item['category']
    obj.created_at = timezone.now()
    obj.save()

print("✅ Overwrote rows. Current newest titles (most recent first):")
for n in News.objects.order_by('-created_at')[:6]:
    print(n.id, "-", n.title)
