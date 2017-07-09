__author__ = 'viktor'
import urllib
import urllib2

class myresponse:
    def __init__(self):
        self.status_code = 0
        self.content = ""

class myrequests:
    @staticmethod
    def post( url, raw_data):
        #encoded_data = urllib.urlencode(raw_data)
        req = urllib2.Request(url, raw_data)
        response = urllib2.urlopen(req)
        r = myresponse()
        r.status_code = response.getcode()
        r.content = response.read()
        return r


