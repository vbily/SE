__author__ = 'viktor'

import httplib2
import os
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

try:
    import argparse
    flags = tools.argparser.parse_args([])
except ImportError:
    flags = None


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/drive-python-quickstart.json
    SCOPES = 'https://www.googleapis.com/auth/drive.metadata.readonly'
    CLIENT_SECRET_FILE = 'client_secrets.json'
    #CLIENT_SECRET_FILE = 'client_secret_se.json'
    APPLICATION_NAME = 'SeamenExchange'

    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')
    #credential_path = "credential.json"
    dir_path = os.path.dirname(os.path.realpath(__file__))
    credential_path = os.path.dirname(os.path.realpath(__file__)) + "/credential.json"
    print credential_path
    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(os.path.dirname(os.path.realpath(__file__)) + CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

def get_books():
    """Shows basic usage of the Google Drive API.

    Creates a Google Drive API service object and outputs the names and IDs
    for up to 10 files.
    """
    import sys
    reload(sys)
    sys.setdefaultencoding('utf8')
    items=[]
    try:
        credentials = get_credentials()
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('drive', 'v2', http=http)
        results = service.files().list().execute()
        items = results.get('items', [])
    
    except Exception as e:
        print type(e)     # the exception instance
        print e.args      # arguments stored in .args
        print e

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print('{0} ({1})'.format(item['title'], item['embedLink']))

    return items
