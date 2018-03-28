import nltk
import re
from flask import Flask
import json
import os
from nltk.tag import StanfordNERTagger
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from flask import Blueprint, request
import googlemaps

app = Flask(__name__)


stopwords = set([w.strip() for w in open('stopwords.txt')])
gmaps = googlemaps.Client(key='AIzaSyCWavyw1CQSTYM4NeH3QG92trkz1va4VQk')

st_ner = StanfordNERTagger('Stanford/english.all.3class.distsim.crf.ser.gz',
                               'Stanford/stanford-ner.jar',
                               encoding='utf-8')

# { Part-of-speech constants
ADJ, ADJ_SAT, ADV, NOUN, VERB = 'a', 's', 'r', 'n', 'v'
# }
def extract(text, lem):
    tokenized_text = nltk.word_tokenize(text)
    pos_text = nltk.pos_tag(tokenized_text)
    word = {'NN':set(),'VB':set(),'ADV':set(),'ADJ':set()}
    for t in pos_text:
        if 'NN' in t[1]:
            # print t[0]
            s = lem.lemmatize(t[0], pos='n')
            word['NN'].add(s)
        if 'VB' in t[1]:
            s = lem.lemmatize(t[0], pos='v')
            word['VB'].add(s)
        if 'RB' in t[1]:
            s = lem.lemmatize(t[0], pos='r')
            word['ADV'].add(s)
        if 'JJ' in t[1]:
            s = lem.lemmatize(t[0], pos='a')
            word['ADJ'].add(s)
    return word


def getBounds(name):
    # Geocoding an address
    geocode_result = gmaps.geocode(name)
    if geocode_result:
        bounds = geocode_result[0]["geometry"]['bounds']
        print bounds
        return bounds
    print 'not return bound'
    return {}

def filterstop_words(s):
    return ' '.join(filter(lambda w: w not in stopwords, s.split()))

def getNER(text):
    tokenized_text = word_tokenize(text)
    classified_text = st_ner.tag(tokenized_text)
    locations = {}
    location_name = ""
    index = 0
    while index < len(classified_text):
        while (index < len(classified_text) and classified_text[index][1] == 'LOCATION'):
            location_name = location_name + classified_text[index][0] + " "
            index = index + 1
        if (location_name != ""):
            location_name = location_name[:-1]
            print location_name
            bounds = getBounds(location_name)
            locations[location_name] = bounds
            location_name = ""
            index = index + 1
        else:
            index = index + 1
    # print locations
    return locations

def set_default(obj):
    if isinstance(obj, set):
        return list(obj)
    raise TypeError

@app.route('/getLocation', methods=['POST'])
def getLocation():
    req = json.loads(request.data)
    lat = req['lat']
    lng = req['lng']
    result = gmaps.reverse_geocode((lat, lng))
    try:
        if result:
            return result[0]['formatted_address']
    except:
        print 'error',lat,' ',lng
        return ""

@app.route('/parseQuery', methods=['POST'])
def parseQuery():
    req = json.loads(request.data)
    text = req['source']
    res = {}
    lem = WordNetLemmatizer()
    # result = re.findall(r'(?:January|March|May|July|August|October|December|September|April|June|Novembe)\s\d{1,2}\w{2}\s\d{4}', text)
    # if result:
    #     print 'date: ', result
    #     res['date'] = result
    #     for x in result:
    #         text = re.sub(x, '',text)

    # (\d \w+(,)* )*(and )*(\d \w+ )ago
    # ((\d\s\w+(,)*\s)*(and\s)*(\d\s\w+\s)ago)|now|tomorrow|(in \d days)
    # regex = ur'(((\d+\s\w+,*\s)*(and\s)*(\d+\s\w+\s)ago)|now|tomorrow|(in \d+ days))'
    # print text
    # match = re.findall(regex, text)
    # if match:
    #     match_date = map(lambda x:str(dateparser.parse(x[0])),match)
    #     res['date'] = match_date
    #     for x in match:
    #         print x[0]
    #         text = re.sub(x[0],'',text)

    text = re.sub(r' +', ' ', text)
    print '\nfilter out date: ', text
    locations = getNER(text)
    if locations:
        res['location'] = locations
        for x in locations.keys():
            text = re.sub(x,'',text)
    word = extract(text, lem)
    res.update(word)
    return json.dumps(res, default=set_default)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=9050, debug=True, threaded=True)
