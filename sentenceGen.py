#!/usr/bin/env python3
import sys
import time
import random
import urllib.parse
import requests
import argparse
import json
import threading
from lxml import html

class Card:
    #replace ; since that's what we'll use as the delimiter for the anki import
    def __init__(self, word, targetSentence, baseSentence):
        self.word = word
        self.targetSentence = targetSentence.strip().replace(";","...")
        self.baseSentence = baseSentence.strip().replace(";", "...")

    def __str__(self):
        return self.targetSentence + " [sound:" + self.word + ".mp3]" + ";" + self.baseSentence

def getConfig(configFilename):
    with open(configFilename) as configFile:
        #TODO: error handling for invalid json in addition to the below check for the presence of all required properties
        configObj = json.load(configFile)
        if not isValidConfig(configObj):
            print("invalid config file; use the -h option for help")
            sys.exit()
        return configObj

#TODO: make this more flexible/less hacky...i.e., ability to go without archaic filtering, etc.
#TODO: make this more robust...are the urls valid? is the xpath expression valid? is the directory valid?
def isValidConfig(configObj):
    return "sentenceSourceUrl" in configObj and "sentenceSourceXpath" in configObj and "sentenceSourceUserAgent" in configObj and "pronunciationSourceUrl" in configObj and "pronunciationBaseDir" in configObj and "wiktionaryBaseUrl" in configObj and "wiktionaryArchaicCategory" in configObj

def readInput(vocabFilename):
    with open(vocabFilename) as vocabFile:
        words = [line.rstrip('\n') for line in vocabFile.readlines()]
        return words

def displayCards(cards):
    for card in cards:
        print(card)

#TODO: may want to make this a standalone script + option for stdout
def filterArchaic(words, wiktionaryBaseUrl, wiktionaryArchaicCategory):
    filtered = []
    isArchaic = False
    for word in words:
        #TODO: add user agent, batching
        response = requests.get(wiktionaryBaseUrl.format(urllib.parse.quote_plus(word)))
        if not wiktionaryArchaicCategory in response.text:
            filtered.append(word)

        #less danger of throttling with wiktionary, but take a short break regardless...
        time.sleep(0.5)
    return filtered

def extractSentence(element):
    sentence = ""
    for child in element.itertext():
        sentence += child.replace('\n', ' ')
    return sentence

def getCard(word, sentenceSourceUrl, sentenceSourceUserAgent, sentenceSourceXpath):
    response = requests.get(sentenceSourceUrl.format(urllib.parse.quote_plus(word)), headers={'user-agent': sentenceSourceUserAgent})
    tree = html.fromstring(response.content)
    elements = tree.xpath(sentenceSourceXpath)

    #let's be nice/avoid them throttling us...
    time.sleep(random.randint(5,10))

    return Card(word, extractSentence(elements[0]), extractSentence(elements[1]))

def getCards(words, config):
    #start making forvo requests and writing the pronunciation files in the background...no need to hold up the main thread, which can continue with sentence gathering
    pronunciationThread = threading.Thread(target=getPronunciations, args=(words, config["pronunciationSourceUrl"], config["pronunciationBaseDir"]))
    pronunciationThread.start()

    cards = []
    for word in words:
        cards.append(getCard(word, config["sentenceSourceUrl"], config["sentenceSourceUserAgent"], config["sentenceSourceXpath"]))

    #the import file should be 100% ready when this script terminates, so wait for pronunciations to come in prior to returning and writing the import file
    pronunciationThread.join()
    return cards

def getPronunciations(words, pronunciationSourceUrl, pronunciationBaseDir):
    for word in words:
        getPronunciation(word, pronunciationSourceUrl, pronunciationBaseDir)

#TODO: retry logic for these requests?
def getPronunciation(word, pronunciationSourceUrl, pronunciationBaseDir):
    audioUrl = getPronunciationAudioUrl(pronunciationSourceUrl, word)
    audioResponse = requests.get(audioUrl)
    if audioResponse.status_code == requests.codes.ok:
        #TODO: handle extension generically?
        #unfortunately, forvo returns it as part of the property name instead of it being part of the value of the property...
        #realistically, we probably shouldn't just trust this random file pulled from some http-only api over the internet, but yolo
        #should likewise not trust the word not to be ../../../../../../../../etc/passwd, but yolo
        writeFile(pronunciationBaseDir + "/" + word + ".mp3", audioResponse.content)

#TODO: make this less reliant on forvo api json structure
def getPronunciationAudioUrl(pronunciationSourceUrl, word):
    response = requests.get(pronunciationSourceUrl.format(urllib.parse.quote_plus(word)))
    if response.status_code == requests.codes.ok:
        responseJson = getJsonContent(response)
        if "items" in responseJson:
            #assuming items, if present, is iterable (it should be an array in the underlying json)
            items = [item for item in responseJson["items"] if "rate" in item and "pathmp3" in item]
            if items:
                #items is non-empty and each item must have a rate and pathmp3 property...get the best-rated mp3 path
                return max(items, key=lambda item: item["rate"])["pathmp3"]

    #something went wrong...no pronunciation url available
    return ""

def getJsonContent(response):
    try:
        return response.json()
    except ValueError:
        print("invalid forvo response" + word, file=sys.stderr)
    return {}

def writeFile(filename, content):
    with open(filename, "wb") as openedFile:
        openedFile.write(content)


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument("configFilename", help="""a json configuration file of the format:\n
{\n
  sentenceSourceUrl: <url ready to be formatted with a word e.g. http://mysentences.com/{0}/exampleSentences>\n
  sentenceSourceXpath: <xpath expression used to extract the sentences from the above url>\n
  sentenceSourceUserAgent: <I uh...just make it look like normal traffic>\n
  pronunciationSourceUrl: <url that can be formatted for a call to forvo e.g. http://apifree.forvo.com/key/<your key>/format/json/action/standard-pronunciation/word/{0}/country/fra>\n
  pronunciationBaseDir: <a directory name where pronunciation audio files will be written (should be anki's collection.media folder, without a trailing slash)>\n
  wiktionaryBaseUrl: <url ready to be formatted to get categories for a word via wiktionary e.g. https://fr.wiktionary.org/w/api.php?action=query&titles={0}&prop=categories&format=json>\n
  wiktionaryArchaicCategory: <the wiktionary category denoting that a word is archaic, e.g. Termes vieillis>
}\n
""")
parser.add_argument("vocabFilename", help="a text file with the words for which you would like to create srs cards, one per line")
args = parser.parse_args()

config = getConfig(args.configFilename)
displayCards(getCards(filterArchaic(readInput(args.vocabFilename), config["wiktionaryBaseUrl"], config["wiktionaryArchaicCategory"]), config))
