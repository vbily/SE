from django.conf.urls import patterns, url, include
from django.utils.translation import ugettext as _

from views import stats_index, stats_check

urlpatterns = patterns('',
    url(r'^%s%s%s$' % (_('admin/'), _('stats/'), _('check/')),  stats_check, name='stats_check'),
)
