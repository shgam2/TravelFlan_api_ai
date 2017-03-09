# -*- coding: utf-8 -*-

import csv
from datetime import datetime
import hashlib
import json
import os
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from flask import make_response, request, Flask
import googlemaps
import requests

app = Flask(__name__)

gmaps = googlemaps.Client(key='AIzaSyB8ri2uUrjtGX2tgOoK_vMSo8ByuP31Njs')

YAHOO_YQL_BASE_URL = 'https://query.yahooapis.com/v1/public/yql?'
TRANSLATE_BASE_URL = 'http://awseb-e-f-AWSEBLoa-VIW6OYVV6CSY-1979702995.us-east-1.elb.amazonaws.com/translate?'

PENGTAI_URL = 'http://www.hanguoing.cn/exApi/travelFlan'
PENGTAI_TEST_URL = 'http://test1.hanguoing.com/exApi/travelFlan'
PENGTAI_KEY = 'xmvoqpfvmffosqksrkqtmqslek'

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
        'chinese': 'zh-cn',
        'simplified chinese': 'zh-cn',
        'traditional chinese': 'zh-tw',
    }.get(lang)


def get_response_template(lang):
    return {
        'en_us': '"%s" in %s is "%s"',
        'zh_hk': '"%s"的%s是"%s"',
        'zh_cn': '"%s"的%s是"%s"',
        'zh_tw': '"%s"的%s是"%s"',
    }.get(lang)


def convert_langauge_to_user_locale(targetlang, userlang):
    if userlang == 'zh_hk' or userlang == 'zh_cn' or userlang == 'zh_tw':
        if targetlang == 'korean':
            return '韩文'
        elif targetlang == 'english':
            return '英文'
        elif targetlang == 'japanese':
            return '日文'
        else:
            return '中文'
    elif userlang == 'en_us':
        if targetlang == 'korean':
            return 'Korean'
        elif targetlang == 'english':
            return 'English'
        elif targetlang == 'japanese':
            return 'Japanese'
        else:
            return 'Chinese'


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


def conv_weather_cond(c_code, lang):
    print('lang is {}'.format(lang))
    weather_file = 'weather_condition.csv'
    try:
        with open(weather_file, 'rU') as f:
            w_cond = list(csv.reader(f))
            row_num = 1
            print('condition = {}'.format(c_code))
            while True:
                print('w_cond[row_num][0] = {}'.format(w_cond[row_num][0]))
                if w_cond[row_num][0] == c_code:
                    row_found = row_num
                    print('found the weather condition! : {}'.format(row_found))
                    break
                elif not w_cond[row_num][0]:
                    print('end of file')
                    break
                else:
                    row_num += 1
    except IOError as e:
        print('IOError: {}'.format(weather_file), e)
    except Exception as e:
        print('Exception', e)

    if lang == 's_cn':
        print('11 {}'.format(w_cond[row_found][2]))
        return w_cond[row_found][2]
    else:
        print('22 {}'.format(w_cond[row_found][3]))
        return w_cond[row_found][3]


def grab_answer(from_loc, to_loc, dir_file, lang):
    try:
        with open(dir_file, 'rU') as f:
            direction = list(csv.reader(f))

            row_num = 0
            col_num = 0

            for i in range(1, 7):
                print('1.{} -- 2.{}'.format(direction[i][0].lower(), from_loc.lower()))
                if direction[i][0].lower() == from_loc.lower():
                    row_num = i
                    break

            for i in range(1, 11):
                if direction[0][i].lower() == to_loc.lower():
                    col_num = i
                    break

            if row_num and col_num:
                speech = direction[row_num][col_num]

                image_url = 'https://s3.ap-northeast-2.amazonaws.com/flanb-data/ai-img/arex.jpg'

                if lang == 'zh_TW' or lang == 'zh_HK':
                    button_title = '點擊查看'
                    title = '仁川國際機場前往首爾市區 | 韓國觀光公社'
                    url = 'http://big5chinese.visitkorea.or.kr/cht/TR/TR_CH_5_18.jsp'
                elif lang == 'zh_CN':
                    button_title = '点击查看'
                    title = '仁川國際機場前往首爾市區 | 韓國觀光公社'
                    url = 'http://big5chinese.visitkorea.or.kr/cht/TR/TR_CH_5_18.jsp'
                else:
                    button_title = 'Click to view'
                    title = 'Korea Tourism Org.: VisitKorea - Transportation - From Incheon Airport to Seoul'
                    url = 'http://english.visitkorea.or.kr/enu/TRP/TP_ENG_2_1.jsp'
                data = [
                    {
                        'attachment_type': 'template',
                        'attachment_template': {
                            'template_type': 'generic',
                            'elements': [
                                {
                                    'title': title,
                                    'image_url': image_url,
                                    'buttons': [
                                        {
                                            'type': 'web_url',
                                            'url': url,
                                            'title': button_title
                                        }
                                    ]
                                }
                            ]
                        }
                    }
                ]
            else:
                speech = None
                data = None
            return speech, data
    except IOError as e:
        print('IOError', e)
    except Exception as e:
        print('Exception', e)


def get_gmap_directions(from_loc, to_loc, lang):
    now = datetime.now()

    # from_loc = gmaps.places(from_loc)['results'][0]['formatted_address']
    # to_loc = gmaps.places(to_loc)['results'][0]['formatted_address']

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
        for i, step in enumerate(directions_result[0]['legs'][0]['steps']):
            route += '%s. %s: %s(%s, %s)\n' % (i, step['travel_mode'], step['html_instructions'],
                                               step['distance']['text'], step['duration']['text'])
            if 'transit_details' in step:
                route += '- %s: %s ~ %s\n' % (step['transit_details']['line']['vehicle']['name'],
                                              step['transit_details']['departure_stop']['name'],
                                              step['transit_details']['arrival_stop']['name'])
            route += '\n'

        speech = 'Fare: %s\n' \
                 'Departure Time: %s\n' \
                 'Arrival Time: %s\n' \
                 'Distance: %s\n' \
                 'Duration: %s\n\n' \
                 'Route:\n%s' % (fare, departure_time, arrival_time, distance, duration, route)

        l = 0
        for x in speech.split('\n'):
            l += len(x)
            if l > 500:
                speech = speech[:l - len(x)] + '\n\n...'
                break
    else:
        speech = 'None'

    map_image_url = 'https://s3.ap-northeast-2.amazonaws.com/flanb-data/ai-img/googlemap_image.jpg'

    if lang == 'zh_TW' or lang == 'zh_HK':
        title = '地圖 - %s -> %s' % (from_loc, to_loc)
        button_title = '點擊查看'
    elif lang == 'zh_CN':
        title = '地图 - %s -> %s' % (from_loc, to_loc)
        button_title = '点击查看'
    else:
        title = 'Map - %s -> %s' % (from_loc, to_loc)
        button_title = 'Click to view'

    data = [
        {
            'attachment_type': 'template',
            'attachment_template': {
                'template_type': 'generic',
                'elements': [
                    {
                        'title': title,
                        'image_url': map_image_url,
                        'buttons': [
                            {
                                'type': 'web_url',
                                'url': url,
                                'title': button_title
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

    from_loc = parameters.get('address-from')
    to_loc = parameters.get('address-to')

    speech, data = grab_answer(from_loc, to_loc, dir_file, lang)
    if not speech:
        speech, data = get_gmap_directions(from_loc, to_loc, lang)
    return speech, data


def exapi_pengtai(data):
    # data = {
    #     'lang': '04',
    #     'category1': '2000',
    #     'category2': '2002',
    #     'cityCode': 'SE',
    #     'areaCode': None,
    #     'latitude': None,
    #     'longitude': None,
    #     'distance': None
    # }
    timestamp = str(int(time.time()))
    plain = '%s|%s' % (PENGTAI_KEY, timestamp)
    headers = {'X-hash': hashlib.sha256(plain.encode('utf-8')).hexdigest()}

    data['timestamp'] = timestamp

    try:
        res = requests.get(PENGTAI_TEST_URL, headers=headers, params=data)
        return json.loads(res.content)
    except Exception as e:
        print(e)
        return None


def process_request(req):
    res = None
    try:
        userlocale = req['originalRequest']['data']['locale'].lower()
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
        city = req['result']['parameters']['geo-city']

        date = req['result']['parameters'].get('date')
        date_period = req['result']['parameters'].get('date-period')

        if not date:
            if not date_period:
                if userlocale == 'zh_cn':
                    temp = conv_weather_cond(condition['code'], 's_cn')
                    speech = '%s的天气: %s, 温度是华氏%s°%s' % (city, temp, condition['temp'], units['temperature'])
                elif userlocale in ('zh_tw', 'zh_hk'):
                    temp = conv_weather_cond(condition['code'], 't_cn')
                    speech = '%s的天氣: %s, 溫度是華氏%s°%s' % (city, temp, condition['temp'], units['temperature'])
                else:
                    speech = 'Current weather in %s: %s, the temperature is %s°%s' % (
                        location['city'], condition['text'],
                        condition['temp'], units['temperature'])
            else:
                if userlocale == 'zh_cn':
                    speech = ('%s天氣預報(10天):' % city)
                elif userlocale in ('zh_tw', 'zh_hk'):
                    speech = ('%s天气预报(10天):' % city)
                else:
                    speech = ('Here is the 10-day forecast for %s:' % (location['city']))

                for i in range(0, 10):
                    item_num = i
                    fc_weather = forecast(date, item_num, forecast_items)

                    if userlocale in ('zh_cn', 'zh_tw', 'zh_hk'):
                        if userlocale == 'zh_cn':
                            lang = 's_cn'
                        else:
                            lang = 't_cn'
                        w_cond = conv_weather_cond(fc_weather['code'], lang)

                        speech += '\n(%s) %s, 高溫: %s°%s, 低溫: %s°%s' % (
                            datetime.strptime(fc_weather['date'], '%d %b %Y').strftime('%m/%d'), w_cond,
                            fc_weather['high'], units['temperature'],
                            fc_weather['low'], units['temperature'])
                        print('speech = {}'.format(speech))
                    else:
                        speech += '\n(%s) %s, high: %s°%s, low: %s°%s' % (
                            datetime.strptime(fc_weather['date'], '%d %b %Y').strftime('%a %b %d'),
                            fc_weather['text'], fc_weather['high'],
                            units['temperature'], fc_weather['low'], units['temperature'])
        else:  # tomorrow portion
            if date == '明天':
                # display 'tomorrow''s weather
                t_date = datetime.strptime(forecast_items[1]['date'], '%d %b %Y').strftime('%m/%d')
                t_code = forecast_items[1]['code']
                t_high = forecast_items[1]['high']
                t_low = forecast_items[1]['low']
                if userlocale == 'zh_cn':
                    speech = '%s的天气(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
                        city, t_date, conv_weather_cond(t_code, 's_cn'),
                        t_high, units['temperature'], t_low, units['temperature']
                    )
                else:
                    speech = '%s的天氣(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
                        city, t_date, conv_weather_cond(t_code, 't_cn'),
                        t_high, units['temperature'], t_low, units['temperature']
                    )
            else:
                item_num = -1
                fc_weather = forecast(date, item_num, forecast_items)

                speech = 'Weather in %s (%s): %s, high: %s°%s, low: %s°%s' % (
                    location['city'], fc_weather['date'], fc_weather['text'],
                    fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature'])

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather'
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
        language = req['result']['parameters']['language']
        code = find_language_code(language.lower())
        print(code)
        url = TRANSLATE_BASE_URL + urlencode({'text': phrase, 'to': code, 'authtoken': 'dHJhdmVsZmxhbjp0b3VyMTIzNA=='})
        print(url)
        _res = urlopen(url).read()
        print(_res)
        tmpl = get_response_template(userlocale)
        print(tmpl)
        language = convert_langauge_to_user_locale(language.lower(), userlocale)
        print(language)
        speech = tmpl % (phrase, language, _res.decode())
        print(speech)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-translate'
        }
    elif action == 'restaurant':
        if userlocale == 'zh_cn':
            lang = '01'
            button_title = '点击查看'
        elif userlocale in ('zh_tw', 'zh_hk'):
            lang = '02'
            button_title = '點擊查看'
        else:
            lang = '04'
            button_title = 'Click to view'

        cuisine = req['result']['parameters']['cuisine'].lower()
        if cuisine == 'korean':
            category2 = '3101'
        elif cuisine == 'japanese':
            category2 = '3102'
        elif cuisine == 'chinese':
            category2 = '3103'
        elif cuisine == 'western':
            category2 = '3104'
        elif cuisine == 'foreign':
            category2 = '3105'
        elif cuisine == 'caffe':
            category2 = '3106'
        elif cuisine == 'fastfood':
            category2 = '3107'
        elif cuisine == 'pub':
            category2 = '3108'
        else:
            category2 = None

        address = req['result']['parameters']['address']
        geocode_result = gmaps.geocode(address)
        latitude = geocode_result[0]['geometry']['location']['lat']
        longitude = geocode_result[0]['geometry']['location']['lng']

        _data = {
            'lang': lang,
            'category1': '3000',
            'category2': category2,
            # 'cityCode': None,
            # 'areaCode': None,
            'latitude': str(latitude),
            'longitude': str(longitude),
            'distance': '500'
        }
        _res = exapi_pengtai(_data)

        speech = ''

        elements = list()
        for i, item in enumerate(_res['list']):
            fb_item = {
                'title': item['name'],
                'subtitle': '%s\n%s' % (item['summary'], item['address']),
                'image_url': item['imagePath'],
                'buttons': [
                    {
                        'type': 'web_url',
                        'url': item['url'],
                        'title': button_title
                    }
                ]
            }
            elements.append(fb_item)

            speech += '%s. name: %s\nsummary: %s\naddress: %s\ntel: %s\nbusiness hours: %s\n\n' % (
                i + 1, item['name'], item['summary'], item['address'], item['tel'], item['besinessHours']
            )

        l = 0
        for x in speech.split('\n'):
            l += len(x)
            if l > 500:
                speech = speech[:l - len(x)] + '\n\n...'
                break

        data = [
            {
                'attachment_type': 'template',
                'attachment_template': {
                    'template_type': 'generic',
                    'elements': elements
                }
            }
        ]

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-restaurant',
            'data': data
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
