import datetime

from forum.settings.base import Setting, SettingSet
from django.utils.translation import ugettext_lazy as _

from base import generate_installation_key

STATS_SET = SettingSet('stats', _('Stats Settings'), _("OSQA Stats Settings."), 100)

CHECK_FOR_UPDATES = Setting('CHECK_FOR_UPDATES', True, STATS_SET, dict(
label = "Check for updates",
help_text = _("""
Use the OSQA stats server recieve notifications about the latest updates.
"""),
required=False))

SITE_KEY = Setting('SITE_KEY', generate_installation_key())

UPDATE_MESSAGES_XML = Setting('UPDATE_MESSAGES_XML', '')

LATEST_UPDATE_DATETIME = Setting('LATEST_UPDATES_DATETIME', datetime.datetime.now())

# Update server. Do not edit.
UPDATE_SERVER_URL = 'https://updater.osqa.net'
