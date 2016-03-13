#!/usr/bin/env python3
import time
import random
import urllib.parse
import fileinput
import requests
from lxml import html

class Card:
    #replace ; since that's what we'll use as the delimiter for the anki import
    def __init__(self, targetSentence, baseSentence):
        self.targetSentence = targetSentence.strip().replace(";","...")
        self.baseSentence = baseSentence.strip().replace(";", "...")

    def __str__(self):
        return self.targetSentence + ";" + self.baseSentence

def readInput():
    words = [line.rstrip('\n') for line in fileinput.input()]
    return words

def displayCards(cards):
    for card in cards:
        print(card)

#TODO: may want to put this as a standalone script + option for stdout
def filterArchaic(words):
    filtered = []
    isArchaic = False
    for word in words:
        #TODO: add user agent, batching...take advantage of dict to pass url params
        response = requests.get("https://fr.wiktionary.org/w/api.php?action=query&titles="+ urllib.parse.quote_plus(word) +"&prop=categories&format=json")
        #TODO: get rid of this hardcoded string; vary per language
        if not "Termes vieillis" in response.text:
            filtered.append(word)

        #less danger of throttling with wiktionary, but take a short break regardless...
        time.sleep(0.5)
    return filtered

def extractSentence(element):
    sentence = ""
    for child in element.itertext():
        sentence += child.strip().replace('\n', ' ') + " "
    return sentence

#TODO: nasty; make independent of reverso page structure/use hypothetical api. Also would need to change per language; could make base url injectable with formattable string
def getCard(word):
    response = requests.get("http://context.reverso.net/translation/french-english/" + urllib.parse.quote_plus(word), headers={'user-agent': '"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.116 Safari/537.36'})
    tree = html.fromstring(response.content)
    elements = tree.xpath('//*[@class="example"][1]//div[@class="text"]')

    #let's avoid them throttling us...
    time.sleep(random.randint(5,10))

    return Card(extractSentence(elements[0]), extractSentence(elements[1]))

def getCards(words):
    cards = []
    for word in words:
        cards.append(getCard(word))
    return cards

displayCards(getCards(filterArchaic(readInput())))

