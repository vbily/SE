from base import *
from tag import Tag
from django.utils.translation import ugettext as _

class TermManager(NodeManager):
    def search(self, keywords, **kwargs):
        return False, self.filter(models.Q(title__icontains=keywords) | models.Q(body__icontains=keywords))

class Term(Node):
    class Meta(Node.Meta):
        proxy = True

    friendly_name = _("term")
    objects = TermManager()

    @property
    def headline(self):
        return self._headline()

    def _headline(self):
        return self.title


    @models.permalink    
    def get_absolute_url(self):
        return ('term', (), {'id': self.id, 'slug': django_urlquote(slugify(self.title))})
        
    def meta_description(self):
        return self.summary

    def get_revision_url(self):
        return reverse('term_revisions', args=[self.id])

    def get_related(self, count=10):
        cache_key = '%s.related_terms:%d:%d' % (settings.APP_URL, count, self.id)
        related_list = cache.get(cache_key)

        if related_list is None:
            related_list = Term.objects.filter_state(deleted=False).values('id').filter(tags__id__in=[t.id for t in self.tags.all()]
            ).exclude(id=self.id).annotate(frequency=models.Count('id')).order_by('-frequency')[:count]
            cache.set(cache_key, related_list, 60 * 60)

        return [Term.objects.get(id=r['id']) for r in related_list]
    

