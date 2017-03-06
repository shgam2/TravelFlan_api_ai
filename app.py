# -*- coding: utf-8 -*-

import csv
import json
import os
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import urlopen

from flask import make_response, request, Flask
import googlemaps

app = Flask(__name__)

YAHOO_YQL_BASE_URL = 'https://query.yahooapis.com/v1/public/yql?'
TRANSLATE_BASE_URL = 'http://awseb-e-f-AWSEBLoa-VIW6OYVV6CSY-1979702995.us-east-1.elb.amazonaws.com/translate?'

# temporary csv files containing answers for transportation-related questions
dir_file_en = 'transportation_en.csv'
dir_file_cn = 'transportation_cn.csv'
dir_file_tw = 'transportation_tw.csv'

# template error messages:
out_of_bound = "Error occured due to one of the following reasons:\n" \
               "1. You must use the language that you signed-up with when asking transportation-related question\n" \
               "2. The origin and/or destination that you've entered is/are not in our database\n" \
               "Please rephrase your transportation-related question and try again!"
rephrase_error = "Please rephrase your transportation-related question.\n" \
                 "Example:\n" \
                 '- English: "How can I go to Kyoto from Osaka?"\n' \
                 '- 简化字: "从大阪要怎样乘车到京都？"\n' \
                 '- 正體字: "由大阪點搭車去京都？"'


def make_yql_query(req):
    city = req['result']['parameters']['geo-city']
    return 'select * from weather.forecast where woeid in (select woeid from geo.places(1) where text=\'%s\') and u=\'c\'' % (city,)


def find_language_code(lang):
    return {
        'korean': 'ko',
        'english': 'en',
        'japanese': 'ja',
        '日文': 'ja',
        '韓文': 'ko',
        '韩文': 'ko',
        '簡體中文': 'zh-cn',
        '简体中文': 'zh-cn',
        '繁體中文': 'zh-tw',
        'chinese simplified': 'zh-cn',
        'chinese traditional': 'zh-tw',
    }.get(lang)


def process_request(req):
    res = None

    action = req['result']['action']
    date = req['result']['parameters'].get('date')
    print("*********date is {}".format(date))
    date_period = req['result']['parameters'].get('date-period')
    print("*********date_period is {}".format(date))

    if action == 'weather':
        url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(req)}) + '&format=json'
        print('YQL-Request:\n%s' % (url,))
        _res = urlopen(url).read()
        print('YQL-Response:\n%s' % (_res,))

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
        forecast_items = data['query']['results']['channel']['item']['forecast']

        if date == "":
            if (date_period == ""):
                speech = 'Weather in %s (current): %s, the temperature is %s °%s' % (location['city'], condition['text'],
                                                                          condition['temp'], units['temperature'])
            else:
                speech = ("Here is the 10-day forecast for %s:" % (location['city']))
                for i in range(0, 10):
                    item_num = i
                    fc_weather = forecast(date, item_num, forecast_items)

                    speech = speech + "\n(%s) %s, high: %s °%s, low: %s °%s" % (
                        datetime.strptime(fc_weather['date'], "%d %b %Y").strftime("%a %b %d"), fc_weather['text'],
                        fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature'])

        else:
            item_num = -1
            fc_weather = forecast(date, item_num, forecast_items)

            speech = 'Weather in %s (%s): %s, high: %s °%s, low: %s °%s' % (
                location['city'], fc_weather['date'], fc_weather['text'],
                fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature'])


        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather'#,
            # 'data': [
            #     {
            #         "attachment_type": "template",
            #         "attachment_template":
            #             {
            #                 'template_type': 'generic',
            #                 'elements': [
            #                     {
            #                         'title': 'TEST!!',
            #                         'image_url': 'https://s3.ap-northeast-2.amazonaws.com/flanb-data/ai-img/q5.png',
            #                         'buttons': [
            #                             {
            #                                 'type': 'web_url',
            #                                 'url': 'https://travelflan.com',
            #                                 'title': 'View'
            #                             }
            #                         ]
            #                     }
            #                 ]
            #             }
            #     },
            #     {
            #         "attachment_type": "image",
            #         "attachment_url": "https://s3.ap-northeast-2.amazonaws.com/flanb-data/ai-img/q5_cn.png"
            #     }
            # ]

        }
    elif action == 'direction':
        speech = parse_json(req)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation'
        }
    elif action == 'translation':
        phrase = req['result']['parameters']['Phrase']
        language = req['result']['parameters']['language']

        code = find_language_code(language.lower())

        url = TRANSLATE_BASE_URL + urlencode({'text': phrase, 'to': code, 'authtoken': 'dHJhdmVsZmxhbjp0b3VyMTIzNA=='})
        _res = urlopen(url).read()

        speech = '"%s" in %s is "%s"' % (phrase, language, _res.decode())
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
    res = json.dumps(res, indent=4)
    print('Response:\n%s' % (res,))

    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def forecast(date, item_num, forecast_items):
    if item_num != -1:
        fc_weather = forecast_items[item_num]
        return fc_weather

    fc_weather = None

    for i in forecast_items:
        if date:
            i_date = datetime.strptime(i.get('date'), "%d %b %Y").strftime("%Y-%m-%d")

            if date == i_date:
                fc_weather = {
                    'date': datetime.strptime(i.get('date'), "%d %b %Y").strftime("%a %b %d"),
                    'high': i.get('high'),
                    'low': i.get('low'),
                    'text': i.get('text')
                }
                print(fc_weather)
                break
    return fc_weather


# input: JSON-formatted requested data
# output: JSON-formatted response data
def parse_json(req):
    lang_code = req['originalRequest']['data'].get('locale')
    if lang_code == "zh_TW" or lang_code == "zh_HK":
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

    speech = grab_answer(loc1, loc2, dir_file)
    return speech


# input:
#   - from_location
#   - to_location
# output:
#   - answer speech (String data)
def grab_answer(loc1, loc2, dir_file):

    try:
        with open(dir_file, 'rU') as f:
            direction = list(csv.reader(f))

            from_loc = loc1
            to_loc = loc2
            count = 0

            while True:
                if direction[count][0] == from_loc:
                    row_num = count
                    count = 0
                    break
                count = count + 1

            while True:
                if direction[0][count] == to_loc:
                    col_num = count
                    count = 0
                    break
                count = count + 1
            speech = direction[row_num][col_num]
            return speech
    except IOError:
        print("exception error")
        # except IndexError:
        # return out_of_bound
    except Exception as e:
        print("something weird happened: ", e)


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print('Starting app on port %d' % port)
    app.run(debug=False, port=port, host='0.0.0.0')
