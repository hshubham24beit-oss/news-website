# attach_images_by_title.py
import os
import django
from django.core.files import File

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from news.models import News
from django.utils import timezone

project_root = os.path.dirname(os.path.abspath(__file__))

# Map exact article title -> local image file (update filenames if yours differ)
mapping = {
    "Breakthrough Cancer Therapy Shows Promising Results": os.path.join(project_root, 'static', 'images', 'thumb1.jpg'),
    "Elections 2025: Key Takeaways from Last Night": os.path.join(project_root, 'static', 'images', 'thumb2.jpg'),
    "New Phone Launch: What's Different This Year": os.path.join(project_root, 'static', 'images', 'thumb3.jpg'),
    "City Wins Comeback Thriller in Final Seconds": os.path.join(project_root, 'static', 'images', 'thumb4.jpg'),
    # optional hero image:
    "Film Festival Highlights: The Year's Best Indies": os.path.join(project_root, 'static', 'images', 'hero.jpg'),
}

attached = 0
for title, img_path in mapping.items():
    try:
        article = News.objects.get(title=title)
    except News.DoesNotExist:
        print("Article not found (title):", title)
        continue

    if not os.path.exists(img_path):
        print("Image file not found:", img_path)
        continue

    with open(img_path, 'rb') as f:
        stored_name = f'news_{article.id}_{os.path.basename(img_path)}'
        # Do NOT change created_at here — we only attach the file
        article.image.save(stored_name, File(f), save=True)
        attached += 1
        print(f"Attached image to article id {article.id} title: {article.title}")

print("Done. Images attached:", attached)
