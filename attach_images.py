# attach_images.py
import os
import django
from django.core.files import File
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from news.models import News

# Map local image paths (source) to article index (0 = newest)
# Adjust names if your files differ
project_root = os.path.dirname(os.path.abspath(__file__))
images = [
    os.path.join(project_root, 'static', 'images', 'thumb1.jpg'),
    os.path.join(project_root, 'static', 'images', 'thumb2.jpg'),
    os.path.join(project_root, 'static', 'images', 'thumb3.jpg'),
    os.path.join(project_root, 'static', 'images', 'thumb4.jpg'),
]

# Strategy: attach these images to the 4 latest articles after the hero
all_news = list(News.objects.order_by('-created_at'))  # newest first
if not all_news:
    print('No News objects found. Add some news first.')
    raise SystemExit(1)

# We want: hero = all_news[0], latest_four = all_news[1:5]
target_articles = all_news[1:5]  # this may be fewer than 4 if DB has less; that's OK

for idx, article in enumerate(target_articles):
    try:
        img_path = images[idx]  # pick corresponding image
    except IndexError:
        print(f'No image defined for article index {idx}; skipping.')
        continue

    if not os.path.exists(img_path):
        print(f'Image file not found: {img_path}; skipping for article id {article.id}')
        continue

    # save image to the ImageField (this will upload to MEDIA_ROOT/news_images/<filename>)
    with open(img_path, 'rb') as f:
        filename = os.path.basename(img_path)
        # optional: prefix filename with article id or timestamp to avoid collisions
        stored_name = f'news_{article.id}_{filename}'
        # remove existing image if you want to replace: article.image.delete(save=False)
        article.image.save(stored_name, File(f), save=True)
        # update modified time so article appears newest if desired:
        article.created_at = timezone.now()
        article.save()
        print(f'Attached {stored_name} to article id {article.id} title: {article.title}')

print('Done attaching images.')
