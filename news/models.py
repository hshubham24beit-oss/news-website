# news/models.py
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse


class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=110, unique=True, blank=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        # auto-generate a unique slug from name if not provided
        if not self.slug:
            base = slugify(self.name) or 'category'
            slug = base
            counter = 1
            # ensure uniqueness, skip self when updating
            while Category.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        # optional: useful for linking directly to a category page by id or slug
        # prefer slug-based route if you add one later; currently we have category by id
        return reverse('news:category_news', args=[self.id])


class News(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='articles')
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('news:news_detail', args=[self.id])
