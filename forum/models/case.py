from base import *
from tag import Tag
from django.utils.translation import ugettext as _

class CaseManager(NodeManager):
    def search(self, keywords, **kwargs):
        return False, self.filter(models.Q(title__icontains=keywords) | models.Q(body__icontains=keywords))

class Case(Node):
    class Meta(Node.Meta):
        proxy = True


    favorite_count = DenormalizedField("actions", action_type="favorite", canceled=False)

    friendly_name = _("case")
    objects = CaseManager()

    @property    
    def view_count(self):
        return self.extra_count

    @property
    def headline(self):
        return self._headline()

    def _headline(self):
        if self.nis.deleted:
            return _('[deleted] ') + self.title

        if self.nis.closed:
            return _('[closed] ') + self.title

        return self.title

    @models.permalink    
    def get_absolute_url(self):
        return ('case', (), {'id': self.id, 'slug': django_urlquote(slugify(self.title))})
        
    def meta_description(self):
        return self.summary

    def get_revision_url(self):
        return reverse('case_revisions', args=[self.id])

    def get_related_questions(self, count=10):
        cache_key = '%s.related_questions:%d:%d' % (settings.APP_URL, count, self.id)
        related_list = cache.get(cache_key)

        if related_list is None:
            related_list = Node.objects.filter_state(deleted=False).values('id').filter(tags__id__in=[t.id for t in self.tags.all()]
            ).exclude(id=self.id).annotate(frequency=models.Count('id')).order_by('-frequency')[:count]
            cache.set(cache_key, related_list, 60 * 60)

        return [Node.objects.get(id=r['id']) for r in related_list]


class CaseRevision(NodeRevision):
    class Meta:
        proxy = True
        
