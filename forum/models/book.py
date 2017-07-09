import datetime
from base import *

from django.db import models

from forum import modules

class Book(BaseModel):
    title            = models.CharField(max_length=255, unique=True)
    url              = models.CharField(max_length=255, unique=True)
    update_date      = models.DateTimeField(default=datetime.datetime.now)
    parent           = models.CharField(max_length=255, unique=True, default='')
    
    def cache_key(self):
        return self._generate_cache_key(Book.safe_cache_title(self.title))
    
    @classmethod
    def safe_cache_title(cls, title):
        return "".join([str(ord(c)) for c in title])
    
    @classmethod
    def infer_cache_key(cls, querydict):
        if 'title' in querydict:
            cache_key = cls._generate_cache_key(cls.safe_cache_title(querydict['title']))
            
            if len(cache_key) > django_settings.CACHE_MAX_KEY_LENGTH:
                cache_key = cache_key[:django_settings.CACHE_MAX_KEY_LENGTH]
            
            return cache_key
        
        return None
    
    @classmethod
    def value_to_list_on_cache_query(cls):
        return 'title'
    
    @models.permalink
    def get_absolute_url(self):
        return ('tag_questions', (), {'tag': self.name})

    
    @models.permalink
    def get_absolute_url(self):
        return ('book', (), {'book': self.url})

    @models.permalink
    def get_title(self):
        return ('title', (), {'book': self.title})

    def __str__(self):
        return self.title


