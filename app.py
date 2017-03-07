# -*- coding: utf-8 -*-

import csv
from datetime import datetime
import json
import os
from urllib.parse import quote, urlencode
from urllib.request import urlopen

from flask import make_response, request, Flask
import googlemaps

app = Flask(__name__)

gmaps = googlemaps.Client(key='AIzaSyB8ri2uUrjtGX2tgOoK_vMSo8ByuP31Njs')

YAHOO_YQL_BASE_URL = 'https://query.yahooapis.com/v1/public/yql?'
TRANSLATE_BASE_URL = 'http://awseb-e-f-AWSEBLoa-VIW6OYVV6CSY-1979702995.us-east-1.elb.amazonaws.com/translate?'

DIR_FILE_EN = 'transportation_en.csv'
DIR_FILE_CN = 'transportation_cn.csv'
DIR_FILE_TW = 'transportation_tw.csv'

OUT_OF_BOUND = 'Error occured due to one of the following reasons:\n' \
               '1. You must use the language that you signed-up with when asking transportation-related question\n' \
               '2. The origin and/or destination that you\'ve entered is/are not in our database\n' \
               'Please rephrase your transportation-related question and try again!'
REPHRASE_ERROR = 'Please rephrase your transportation-related question.\n' \
                 'Example:\n' \
                 '- English: "How can I go to Kyoto from Osaka?"\n' \
                 '- 简化字: "从大阪要怎样乘车到京都？"\n' \
                 '- 正體字: "由大阪點搭車去京都？"'


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

def get_response_template(lang):
    return {
        'en_us': '"%s"的%s是%s',
        'zh_hk': '"%s"的%s是%s',
        'zh_cn': '"%s"的%s是%s',
        'zh_tw': '"%s"的%s是%s',
    }.get(lang)


def make_yql_query(req):
    city = req['result']['parameters']['geo-city']
    return 'select * from weather.forecast ' \
           'where woeid in (select woeid from geo.places(1) where text=\'%s\') and u=\'c\'' % (city,)


def forecast(date, item_num, forecast_items):
    if item_num != -1:
        fc_weather = forecast_items[item_num]
        return fc_weather

    fc_weather = None

    for i in forecast_items:
        if date:
            i_date = datetime.strptime(i.get('date'), '%d %b %Y').strftime('%Y-%m-%d')

            if date == i_date:
                fc_weather = {
                    'date': datetime.strptime(i.get('date'), '%d %b %Y').strftime('%a %b %d'),
                    'high': i.get('high'),
                    'low': i.get('low'),
                    'text': i.get('text')
                }
                print(fc_weather)
                break
    return fc_weather


def grab_answer(from_loc, to_loc, dir_file):
    try:
        with open(dir_file, 'rU') as f:
            direction = list(csv.reader(f))

            row_num = 0
            col_num = 0

            for i in range(1, 3):
                if direction[i][0] == from_loc:
                    row_num = i
                    break

            for i in range(1, 3):
                if direction[0][i] == to_loc:
                    col_num = i
                    break

            if row_num and col_num:
                speech = direction[row_num][col_num]
            else:
                speech = None
            return speech, None
    except IOError as e:
        print('IOError', e)
    except Exception as e:
        print('Exception', e)


def get_gmap_directions(from_loc, to_loc, lang):
    now = datetime.now()

    from_loc = gmaps.places(from_loc, language=lang)['results'][0]['formatted_address']
    to_loc = gmaps.places(to_loc, language=lang)['results'][0]['formatted_address']

    url = 'https://www.google.com/maps?saddr=%s&daddr=%s&dirflg=r' % (
        from_loc.replace(' ', '+'), to_loc.replace(' ', '+'))

    directions_result = gmaps.directions(from_loc, to_loc, mode='transit', departure_time=now, language=lang)
    if directions_result:
        fare = directions_result[0]['fare']['text']
        departure_time = directions_result[0]['legs'][0]['departure_time']['text']
        arrival_time = directions_result[0]['legs'][0]['arrival_time']['text']
        distance = directions_result[0]['legs'][0]['distance']['text']
        duration = directions_result[0]['legs'][0]['duration']['text']

        route = ''
        for step in directions_result[0]['legs'][0]['steps']:
            route += '%s: %s(%s, %s)' % (step['travel_mode'], step['html_instructions'],
                                         step['distance']['text'], step['duration']['text'])
            if 'transit_details' in step:
                route += '- %s: %s ~ %s' % (step['transit_details']['line']['vehicle']['name'],
                                            step['transit_details']['departure_stop']['name'],
                                            step['transit_details']['arrival_stop']['name'])

        speech = 'Fare: %s\n' \
                 'Departure Time: %s\n' \
                 'Arrival Time: %s\n' \
                 'Distance: %s\n' \
                 'Duration: %s\n' \
                 'Route:\n%s' % (fare, departure_time, arrival_time, distance, duration, route)
        speech = speech[:600]
    else:
        speech = ' '
    data = [
        {
            "attachment_type": "template",
            "attachment_template": {
                'template_type': 'generic',
                'elements': [
                    {
                        'title': 'Map',
                        'buttons': [
                            {
                                'type': 'web_url',
                                'url': url,
                                'title': 'View'
                            }
                        ]
                    }
                ]
            }
        }
    ]

    return speech, data


def parse_json(req):
    lang = req['originalRequest']['data'].get('locale')
    if lang == 'zh_TW' or lang == 'zh_HK':
        dir_file = DIR_FILE_TW
    elif lang == 'zh_CN':
        dir_file = DIR_FILE_CN
    else:
        dir_file = DIR_FILE_EN

    result = req.get('result')
    parameters = result.get('parameters')

    from_loc = parameters.get('direction1')
    to_loc = parameters.get('direction2')

    speech, data = grab_answer(from_loc, to_loc, dir_file)
    if not speech:
        speech, data = get_gmap_directions(from_loc, to_loc, lang)
    return speech, data


def process_request(req):
    res = None
    try:
        userlocale = req['originalRequest']['data']['locale']
    except Exception as e:
        userlocale = 'zh_cn'
    action = req['result']['action']
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

        date = req['result']['parameters'].get('date')
        date_period = req['result']['parameters'].get('date-period')

        if not date:
            if not date_period:
                speech = 'Weather in %s (current): %s, the temperature is %s °%s' % (
                    location['city'], condition['text'],
                    condition['temp'], units['temperature'])
            else:
                speech = ('Here is the 10-day forecast for %s:' % (location['city']))
                for i in range(0, 10):
                    item_num = i
                    fc_weather = forecast(date, item_num, forecast_items)

                    speech += '\n(%s) %s, high: %s °%s, low: %s °%s' % (
                        datetime.strptime(fc_weather['date'], '%d %b %Y').strftime('%a %b %d'),
                        fc_weather['text'], fc_weather['high'],
                        units['temperature'], fc_weather['low'], units['temperature'])

        else:
            item_num = -1
            fc_weather = forecast(date, item_num, forecast_items)

            speech = 'Weather in %s (%s): %s, high: %s °%s, low: %s °%s' % (
                location['city'], fc_weather['date'], fc_weather['text'],
                fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature'])

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather',
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
        speech, data = parse_json(req)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation',
            'data': data
        }
    elif action == 'translation':
        phrase = req['result']['parameters']['Phrase']
        language = req['result']['parameters']['language'][0]
        code = find_language_code(language.lower())

        print(code)
        url = TRANSLATE_BASE_URL + urlencode({'text': phrase, 'to': code, 'authtoken': 'dHJhdmVsZmxhbjp0b3VyMTIzNA=='})
        print(url)
        _res = urlopen(url).read()
        print(_res)
        tmpl = get_response_template(userlocale.lower())
        print(tmpl)
        speech = tmpl % (phrase, language, _res.decode())
        print(speech)
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


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print('Starting app on port %d' % port)
    app.run(debug=False, port=port, host='0.0.0.0')
