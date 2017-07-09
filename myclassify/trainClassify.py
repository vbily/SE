import textract
from bs4 import BeautifulSoup
import urllib2
import os
from myclassify import myclassify

def download_file(download_url, file_name):
    response = urllib2.urlopen(download_url)
    file = open(file_name, 'w')
    file.write(response.read())
    file.close()
    print("Download completed: " + download_url)

def trainMANServiceLetters():
    resp = urllib2.urlopen("http://marine.man.eu/two-stroke/service-letters/page/14")
    soup = BeautifulSoup(resp, from_encoding=resp.info().getparam('charset'))

    for link in soup.find_all('a', href=True):
        if ".pdf" in link['href']:
            print link['href']
            download_file(link['href'], "temp.pdf")
            fname = os.getcwd() + '/temp.pdf'
            print fname
            text = textract.process(fname)
            a.train([text],"Engineering","MarineKnowledge")
            print "done"

def trainSeamenExchangeSpam():
    file = open("/tmp/output.csv", 'r')
    raw_html = file.read()
    file.close()
    cleantext = BeautifulSoup(raw_html).text.encode('utf-8')
    a.train([cleantext],"NotRelated","MarineKnowledge")


def trainMarineInsight(site_category, page, classifier_category):
    resp = urllib2.urlopen("http://www.marineinsight.com/category/" + site_category + "/page/"+str(page))
    soup = BeautifulSoup(resp, from_encoding=resp.info().getparam('charset'))
    links = []
    for link in soup.find_all('a', href=True):
        if (link['href'].startswith("http://www.marineinsight.com/" + site_category)) and (not (link['href'] in links)):
            print link['href']
            links.append(link['href'])
            response = urllib2.urlopen(link['href'])
            soup2 = BeautifulSoup(response, from_encoding=response.info().getparam('charset'))
            for t in soup2.find_all('div',{'class' : 'pbs-main-wrapper'}, limit=None):
                a.train([t.get_text().encode('utf-8')],classifier_category,"MarineKnowledge")

def trainTime(page, classifier_category):
    resp = urllib2.urlopen("http://time.com/newsfeed/page/"+str(page))
    soup = BeautifulSoup(resp, from_encoding=resp.info().getparam('charset'))
    links = []
    for link in soup.find_all('h2',{'class':'section-article-title'}):
        if not (link.contents[0]['href'] in links):
            print link.contents[0]['href']
            links.append(link.contents[0]['href'])
            response = urllib2.urlopen(link.contents[0]['href'])
            soup2 = BeautifulSoup(response, from_encoding=response.info().getparam('charset'))
            for t in soup2.find_all('article',{'class' : 'row'}, limit=None):
                a.train([t.get_text().encode('utf-8')],classifier_category,"MarineKnowledge")




a = myclassify()
a.setWriteApiKey('J42r0FybyBxK')
a.setReadApiKey('KQOiTh2yCzd1')
#trainMarineInsight("marine-safety",6,"Safety")
#trainTime(2, "NotRelated")
d=a.classify(["Chief Mate"], "MarineKnowledge")
print d
print float(d[0][2][2][1]) > 0.5