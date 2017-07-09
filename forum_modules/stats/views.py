from django.http import HttpResponse
from django.utils.translation import ugettext as _

from base import check_for_updates

from forum.views.admin import admin_tools_page, admin_page

@admin_tools_page(_('stats'), _('Stats Module'))
def stats_index(request):
    return (
        'modules/stats/index.html',
        {

        },
    )

def stats_check(request):
    update_status = check_for_updates()

    return HttpResponse(update_status, mimetype='text/html')
