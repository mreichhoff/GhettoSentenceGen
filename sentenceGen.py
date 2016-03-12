#!/usr/bin/env python3
import time
import random
import urllib.parse
import fileinput
import requests
from lxml import html

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
        #TODO: add user agent, batching...take advantage of dict to pass url params
        response = requests.get("https://fr.wiktionary.org/w/api.php?action=query&titles="+ urllib.parse.quote_plus(word) +"&prop=categories&format=json&clcategories=Cat%C3%A9gorie:Termes%20vieillis%20en%20fran%C3%A7ais")
        #TODO: get rid of this hardcoded string; vary per language
        if not "Termes vieillis" in response.text:
            filtered.append(word)

        #less danger of throttling with wiktionary, but take a short break regardless...
        time.sleep(0.5)
    return filtered

#TODO: nasty; make independent of reverso page structure/use hypothetical api. Also would need to change per language; could make base url injectable with formattable string
def getSentence(word):
    sentence = ""
    response = requests.get("http://context.reverso.net/translation/french-english/" + urllib.parse.quote_plus(word), headers={'user-agent': '"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'})

    tree = html.fromstring(response.content)
    elements = tree.xpath('//*[@class="example"][1]//div[@class="text"]')
    i=0;
    for element in elements:
        for element in elements[i].itertext():
            sentence += element.strip().replace('\n', ' ') + " "
        sentence += "\n"
        i+=1

    #let's avoid them throttling us...
    time.sleep(random.randint(5,10))

    return sentence

def getSentences(words):
    sentences = []
    for word in words:
        sentences.append(getSentence(word))
    return sentences

displayWords(getSentences(filterArchaic(readInput())))

