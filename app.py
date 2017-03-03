# -*- coding: utf-8 -*-

from __future__ import print_function
from future.standard_library import install_aliases

install_aliases()

import json
import os
import csv
import requests
import unicodecsv
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from flask import make_response, request, Flask

app = Flask(__name__)

YAHOO_YQL_BASE_URL = 'https://query.yahooapis.com/v1/public/yql?'
TRANSLATE_BASE_URL = 'http://awseb-e-f-AWSEBLoa-VIW6OYVV6CSY-1979702995.us-east-1.elb.amazonaws.com/translate?'

# temporary csv files containing answers for transportation-related questions
dir_file_en = 'transportation_en.csv'
dir_file_cn = 'transportation_cn.csv'
dir_file_tw = 'transportation_tw.csv'

def make_yql_query(req):
    city = req['result']['parameters']['geo-city']
    return 'select * from weather.forecast where woeid in (select woeid from geo.places(1) where text=\'%s\')' % (city,)


def find_language_code(lang):
    return {
        'korean': 'ko',
        'english': 'en',
        'japanese': 'ja',
        'chinese simplified': 'zh-cn',
        'chinese traditional': 'zh-tw',
    }.get(lang)

def process_request(req):
    res = None

    action = req['result']['action']
    if action == 'weather':
        url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(req)}) + '&format=json'
        # print('YQL-Request:\n%s' % (url,))
        _res = urlopen(url).read()
        # print('YQL-Response:\n%s' % (_res,))

        data = json.loads(_res)

        if 'query' not in data:
            return res
        if 'results' not in data['query']:
            return res
        if 'channel' not in data['query']['results']:
            return res

        for x in ('location', 'item', 'units'):
            if x not in data['query']['results']['channel']:
                return res

        if 'condition' not in data['query']['results']['channel']['item']:
            return res

        location = data['query']['results']['channel']['location']
        condition = data['query']['results']['channel']['item']['condition']
        units = data['query']['results']['channel']['units']

        speech = 'Weather in %s: %s, the temperature is %s %s' % (location['city'], condition['text'],
                                                                  condition['temp'], units['temperature'])
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather'
        }
    elif action == 'direction':
        speech = parse_json(req)
        print ("111111111111")
        print (speech)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-direction'
        }
    elif action == 'translation':
        print("translate block entered")
        print(json.dumps(req['result'], indent=4))
        phrase = req['result']['parameters']['Phrase']
        language = req['result']['parameters']['language']
        code = find_language_code(language.lower())

        print(phrase)
        print(language)
        print(code)

        url = TRANSLATE_BASE_URL + urlencode({'text': phrase, 'to': code, 'authtoken': 'dHJhdmVsZmxhbjp0b3VyMTIzNA==' })
        print(url)
        _res = urlopen(url).read()
        print('im here1')
        print(json.dumps(_res, indent=4))
        translated = str(json.dumps(_res, indent=4)).decode('iso-8859-1').encode('utf8')
        speech = '"%s" in %s is "%s"' % (phrase, language, translated)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-translate'
        }
    return res

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    print('Request:\n%s' % (json.dumps(req, indent=4),))

    res = process_request(req)
    print ("RESSS")
    print (res)
    try:
        res = json.dumps(res, indent=4)
    except Exception as e:
        print (e)
    print('Response:\n%s' % (res,))

    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


# input: JSON-formatted requested data
# output: JSON-formatted response data
def parse_json(req):
    # print("in parse_json method")
    # print("----------------req --------------------")
    # print(req)
    # print("----------------req --------------------")
    #if req.get['originalRequest'] is None:
    #    dir_file = dir_file_en
    #else:
    lang_code = req['originalRequest']['data'].get('locale')
    #print ("**************lang_code = {}".format(lang_code))
    if lang_code == "zh_HK":
        # use traditional chinese
        dir_file = dir_file_tw
    elif lang_code == "zh_CN":
        # use simplified chinese
        dir_file = dir_file_cn
    else:
        # use english
        dir_file = dir_file_en


    result = req.get("result")
    parameters = result.get("parameters")

    loc1 = parameters.get("direction1")
    loc2 = parameters.get("direction2")
    if (loc1 is None) or (loc2 is None):
        return None

    # print("-------------------------------------------------")
    # print("loc1 = {}".format(loc1))
    # print("loc2 = {}".format(loc2))
    # print("-------------------------------------------------")
    speech = grab_answer(loc1, loc2, dir_file)
    print("Response:")
    print(speech)
    return speech


# input:
#   - from_location
#   - to_location
# output:
#   - answer speech (String data)
def grab_answer(loc1, loc2, dir_file):
    print("in grab_answer function")
    print("filename = {}".format(dir_file))

    try:
        with open(dir_file, 'rU') as f:
            direction = list(unicodecsv.reader(f, encoding='utf-8'))

            from_loc = loc1
            to_loc = loc2
            row_num = 0
            col_num = 0
            count = 0

            print("from_loc = {}".format(from_loc))
            print("to_loc = {}".format(to_loc))

            while True:
                print("inside loop now!!")
                if direction[count][0] == "":
                    # location not found
                    break
                if direction[count][0] == from_loc:
                    row_num = count
                    count = 0
                    print("rownum = {}".format(row_num))
                    break
                count = count + 1

            while True:
                if direction[0][count] == "":
                    # location not found
                    break
                if direction[0][count] == to_loc:
                    col_num = count
                    count = 0
                    print("colnum = {}".format(col_num))
                    break
                count = count + 1
            print(direction[row_num][col_num])
            speech = direction[row_num][col_num]
            return speech
    except IOError:
        print("exception error")
    except Exception as e:
        print("something weird happened", e)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print('Starting app on port %d' % port)
    app.run(debug=False, port=port, host='0.0.0.0')
