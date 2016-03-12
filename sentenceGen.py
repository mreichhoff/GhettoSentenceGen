#!/usr/bin/env python3
import sys
import subprocess
import time
import re
import random
import urllib.parse
import xml.sax.saxutils
import fileinput

def readInput():
    words = [line.rstrip('\n') for line in fileinput.input()]
    return words

def displayWords(words):
    for word in words:
        print(word)

#TODO: may want to put this as a standalone script + option for stdout
def filterArchaic(words):
    filtered = []
    isArchaic = False
    for word in words:
        #TODO: add user agent, batching?
        proc = subprocess.Popen('curl https://fr.wiktionary.org/w/api.php?action=query\\&titles=' + urllib.parse.quote_plus(word) + '\\&prop=categories\\&format=json\\&clcategories=Cat%C3%A9gorie:Termes%20vieillis%20en%20fran%C3%A7ais 2>/dev/null', stdout=subprocess.PIPE, shell=True, universal_newlines=True)
        for line in proc.stdout.readlines():
            #TODO: grep above instead of if here; add variation of archaic category per language?
            if "Termes vieillis" in line:
                isArchaic = True
                break
        if not isArchaic:
            filtered.append(word)
        isArchaic = False
        #less danger of throttling with wiktionary, but take a short break regardless...
        time.sleep(0.5)
    return filtered

#TODO: nasty; make independent of reverso page structure/use hypothetical api. Also would need to change per language; could make base url injectable with formattable string
def getExampleHtml(word):
    sentence = ""
    
    #https://requests.readthedocs.org/en/master/
    #http://docs.python-guide.org/en/latest/scenarios/scrape/
    #import urllib.request
    #req = urllib.request.Request("http://context.reverso.net/translation/french-english/cocher", headers={"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36"})
    #urllib.request.urlopen(req).read();

    #yeah, yeah, security issue since we can't really trust the word and are running in shell mode. whatever.
    proc = subprocess.Popen('curl -A "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36" http://context.reverso.net/translation/french-english/' + urllib.parse.quote_plus(word) + ' 2>/dev/null | xmllint --recover --html --xpath \'//*[@class="example"][1]//div[@class="text"]\' - 2>/dev/null', stdout = subprocess.PIPE, shell=True, universal_newlines=True)
    for line in proc.stdout.readlines():
        sentence += line.strip()

    #let's avoid them throttling us...
    time.sleep(random.randint(5,10))

    return sentence

def getSentence(html):
    pattern = re.compile("<a[^>]*>")
    return xml.sax.saxutils.unescape(re.sub(pattern, "", html.replace("<div class=\"text\">", "\n").replace("</div>", "").replace("<em>", "").replace("</em>", "").replace("</a>", "")))

def getSentences(words):
    sentences = []
    for word in words:
        sentences.append(getSentence(getExampleHtml(word)))
    return sentences

displayWords(getSentences(filterArchaic(readInput())))

