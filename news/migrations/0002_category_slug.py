# news/migrations/0002_category_slug.py
from django.db import migrations, models
import django.utils.timezone

def populate_slugs(apps, schema_editor):
    from django.utils.text import slugify
    Category = apps.get_model('news', 'Category')

    for c in Category.objects.all():
        if not getattr(c, 'slug', None):
            base = slugify(c.name) or 'category'
            slug = base
            counter = 1
            # ensure uniqueness within the table
            while Category.objects.filter(slug=slug).exclude(pk=c.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            c.slug = slug
            c.save()

class Migration(migrations.Migration):

    dependencies = [
        ('news', '0001_initial'),
    ]

    operations = [
        # 1) Add slug field allowing NULL so adding it to existing rows won't violate unique constraint
        migrations.AddField(
            model_name='category',
            name='slug',
            field=models.SlugField(max_length=110, unique=True, null=True, blank=True),
        ),

        # 2) Populate slug values for existing rows
        migrations.RunPython(populate_slugs, reverse_code=migrations.RunPython.noop),

        # 3) Alter field to make it non-nullable (and keep unique=True)
        migrations.AlterField(
            model_name='category',
            name='slug',
            field=models.SlugField(max_length=110, unique=True, null=False, blank=True),
        ),
    ]
