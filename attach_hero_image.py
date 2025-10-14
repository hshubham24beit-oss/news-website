# attach_hero_image.py
import os
import django
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from news.models import News

project_root = os.path.dirname(os.path.abspath(__file__))
img_path = os.path.join(project_root, 'static', 'images', 'hero.jpg')  # change if path/name differs

if not os.path.exists(img_path):
    print("Image not found:", img_path)
    raise SystemExit(1)

# choose the hero article (newest)
hero = News.objects.order_by('-created_at').first()
if not hero:
    print("No News articles found.")
    raise SystemExit(1)

with open(img_path, 'rb') as f:
    # optionally prefix to avoid filename collision
    stored_name = f'hero_{hero.id}_{os.path.basename(img_path)}'
    # delete old image if you want: hero.image.delete(save=False)
    hero.image.save(stored_name, File(f), save=True)

print("Attached image to hero article:", hero.id, hero.title)
