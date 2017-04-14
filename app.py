# -*- coding: utf-8 -*-

import csv
import datetime
from datetime import datetime, timedelta
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

TF_ITINERARY_URL = 'https://flanb-demo.travelflan.com/data/itinerary?type=0&'
TF_TOUR_URL = 'https://flanb-demo.travelflan.com/data/itinerary?type=1&days=1&'

PENGTAI_URL = 'http://www.hanguoing.cn/exApi/travelFlan'
PENGTAI_TEST_URL = 'http://test1.hanguoing.com/exApi/travelFlan'
PENGTAI_KEY = 'xmvoqpfvmffosqksrkqtmqslek'

GURUNAVI_KEY = '6d98dbe7eca799250d844be0426a3bad'
GURUNAVI_SEARCH_URL = 'https://api.gnavi.co.jp/ForeignRestSearchAPI/20150630/?'
GURUNAVI_AREA_URL = 'https://api.gnavi.co.jp/master/GAreaLargeSearchAPI/20150630/?'
GURUNAVI_CATEGORY_URL = 'https://api.gnavi.co.jp/master/CategoryLargeSearchAPI/20150630/?'

MAP_IMAGE_URL = 'https://s3.ap-northeast-2.amazonaws.com/flanb-data/ai-img/googlemap_image.jpg'

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


def make_yql_query(req, city):
    # city = req['result']['parameters']['city']
    # print ("city here is {}".format(req['result']['parameters']['city']))
    return 'select * from weather.forecast ' \
           'where woeid in (select woeid from geo.places(1) where text=\'%s\') and u=\'c\'' % (city,)


def forecast(date, item_num, forecast_items):
    if item_num != -1:
        fc_weather = forecast_items[item_num]
        return fc_weather

    for i in forecast_items:
        if date:
            i_date = datetime.strptime(i.get('date'), '%d %b %Y').strftime('%Y-%m-%d')
            if date == i_date:
                fc_weather = {
                    'date': datetime.strptime(i.get('date'), '%d %b %Y').strftime('%a %b %d'),
                    'high': i.get('high'),
                    'low': i.get('low'),
                    'text': i.get('text'),
                    'code': i.get('code')
                }
                return fc_weather
                # break
    print("We've got past the forecast_items")
    return None


def conv_weather_cond(c_code, lang):
    weather_file = 'weather_condition.csv'
    try:
        with open(weather_file, 'rU') as f:
            w_cond = list(csv.reader(f))
            row_num = 1
            print('condition = {}'.format(c_code))
            while True:
                # print('w_cond[row_num][0] = {}'.format(w_cond[row_num][0]))
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

            print("1.{} 2.{}".format(from_loc, to_loc))

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
                        'attachment_payload': {
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
    print('from_loc = %s' % (from_loc))
    print('to_loc = %s' % (to_loc))
    # from_loc = gmaps.places(from_loc)['results'][0]['formatted_address']
    # to_loc = gmaps.places(to_loc)['results'][0]['formatted_address']

    if lang in ('zh_CN', 'zh_TW', 'zh_HK'):
        url = 'http://maps.google.cn/maps?saddr=%s&daddr=%s&dirflg=r' % (
            from_loc.replace(' ', '+'), to_loc.replace(' ', '+'))
    else:
        url = 'https://www.google.com/maps?saddr=%s&daddr=%s&dirflg=r' % (
            from_loc.replace(' ', '+'), to_loc.replace(' ', '+'))

    directions_result = gmaps.directions(from_loc, to_loc, mode='transit', departure_time=now, language=lang)
    if directions_result:
        fare = None
        departure_time = None
        arrival_time = None
        distance = None
        duration = None
        if 'fare' in directions_result[0]:
            fare = directions_result[0]['fare']['text']
        if 'departure_time' in directions_result[0]:
            departure_time = directions_result[0]['legs'][0]['departure_time']['text']
        if 'arrival_time' in directions_result[0]:
            arrival_time = directions_result[0]['legs'][0]['arrival_time']['text']
        if 'distance' in directions_result[0]:
            distance = directions_result[0]['legs'][0]['distance']['text']
        if 'duration' in directions_result[0]:
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

        if lang == 'zh_TW' or lang == 'zh_HK':
            speech = '費用: %s\n' \
                     '出發時間: %s\n' \
                     '抵達時間: %s\n' \
                     '距離: %s\n' \
                     '所需時間: %s\n\n' \
                     '路線:\n%s' % (fare, departure_time, arrival_time, distance, duration, route)
        elif lang == 'zh_CN':
            speech = '费用: %s\n' \
                     '出发时间: %s\n' \
                     '抵达时间: %s\n' \
                     '距离: %s\n' \
                     '所需时间: %s\n\n' \
                     '路线:\n%s' % (fare, departure_time, arrival_time, distance, duration, route)
        else:
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
        speech = ''  # Need to change this to None without quotes? ###########

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
            'attachment_payload': {
                'template_type': 'generic',
                'elements': [
                    {
                        'title': title,
                        'image_url': MAP_IMAGE_URL,
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
    if req['originalRequest']['data'].get('locale'):
        lang = req['originalRequest']['data'].get('locale')
    else:
        lang = 'zh_CN'
    if lang == 'zh_CN':
        dir_file = DIR_FILE_CN
    elif lang in ('zh_TW', 'zh_HK'):
        dir_file = DIR_FILE_TW
    else:
        dir_file = DIR_FILE_EN

    result = req.get('result')
    parameters = result.get('parameters')

    if parameters.get('address-from'):
        from_loc = parameters.get('address-from')
    else:
        from_loc = parameters.get('prev-address-from')

    if parameters.get('address-to'):
        to_loc = parameters.get('address-to')
    else:
        to_loc = parameters.get('prev-address-to')

    speech, data = grab_answer(from_loc, to_loc, dir_file, lang)
    if not speech:
        speech, data = get_gmap_directions(from_loc, to_loc, lang)
    return speech, data


def exapi_travelflan_itin(data):
    if data['theme'] in ('Food', '美食'):
        theme = 1
    elif data['theme'] in ('Shopping', '购物', '購物'):
        theme = 2
    elif data['theme'] in ('Kids', '亲子', '親子'):
        theme = 3
    elif data['theme'] in ('Suburbs', '近郊'):
        theme = 4
    else:
        theme = 0

    itinerary_url = TF_ITINERARY_URL + urlencode({'area': data['city'].lower(),
                                                  'days': data['num_days'],
                                                  'theme': theme})
    print('itinerary_url:', itinerary_url)

    try:
        res = requests.get(itinerary_url)
        return res.json()
    except Exception as e:
        print(e)
        return None


def exapi_travelflan_tour(data):
    tour_url = TF_TOUR_URL + urlencode({'area': data['city']})
    print('tour_url:', tour_url)

    try:
        res = requests.get(tour_url)
        return res.json()
    except Exception as e:
        print(e)
        return None


def exapi_pengtai(data):
    timestamp = str(int(time.time()))
    plain = '%s|%s' % (PENGTAI_KEY, timestamp)
    headers = {'X-hash': hashlib.sha256(plain.encode('utf-8')).hexdigest()}

    data['timestamp'] = timestamp

    try:
        res = requests.get(PENGTAI_TEST_URL, headers=headers, params=data)
        print('thomas1')
        print(res.json())
        return res.json()
    except Exception as e:
        print(e)
        return None


def process_request(req):
    res = None
    print('1111111')
    try:
        userlocale = req['originalRequest']['data']['locale'].lower()
    except Exception as e:
        userlocale = 'zh_cn'
    print('req is {}'.format(req))
    print('222222222')
    action = req['result']['action']

    print('111 action is {}'.format(action))
    if action == 'prev_context':
        action = req['result']['parameters'].get('prev-action')
        if req['result']['parameters'].get('city'):
            city = req['result']['parameters']['city']
        elif not req['result']['parameters'].get('city') and req['result']['parameters'].get('prev-city'):
            city = req['result']['parameters'].get('prev-city')
        else:
            None
    else:
        if req['result']['parameters'].get('city'):
            city = req['result']['parameters'].get('city')

    if action == 'weather':
        url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(req, city)}) + '&format=json'
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
        prev_date = req['result']['parameters'].get('prev-date')
        date_period = req['result']['parameters'].get('date-period')
        prev_dp = req['result']['parameters'].get('prev-dp')
        if prev_dp and not date:
            date_period = prev_dp
        if prev_date and not date_period:
            date = prev_date
        if not date or (date and date_period):
            # current weather
            if not date_period:
                if userlocale == 'zh_cn':
                    temp = conv_weather_cond(condition['code'], 's_cn')
                    speech = '%s的天气: %s, 温度是%s°%s' % (city, temp, condition['temp'], units['temperature'])
                elif userlocale in ('zh_tw', 'zh_hk'):
                    temp = conv_weather_cond(condition['code'], 't_cn')
                    speech = '%s的天氣: %s, 溫度是%s°%s' % (city, temp, condition['temp'], units['temperature'])
                else:
                    speech = 'Current weather in %s: %s, the temperature is %s°%s' % (
                        location['city'], condition['text'],
                        condition['temp'], units['temperature'])
            # 10-day weather forecast
            else:
                check_date1 = date_period.partition('/')[0]
                check_date2 = date_period.partition('/')[2]
                check_date1 = datetime.strptime(check_date1, '%Y-%m-%d')
                check_date2 = datetime.strptime(check_date2, '%Y-%m-%d')
                if check_date1 > datetime.strptime(forecast_items[9]['date'],
                                                   '%d %b %Y') or check_date2 < datetime.strptime(
                    forecast_items[0]['date'], '%d %b %Y'):
                    return None

                if userlocale == 'zh_cn':
                    speech = ('%s天氣預報(10天):' % city)
                elif userlocale in ('zh_tw', 'zh_hk'):
                    speech = ('%s天气预报(10天):' % city)
                else:
                    speech = ('Here is the 10-day forecast for %s:' % (location['city']))

                for i in range(0, 10):
                    item_num = i
                    fc_weather = forecast(date, item_num, forecast_items)
                    if fc_weather == None:
                        speech = None
                        break
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
                    else:
                        speech += '\n(%s) %s, high: %s°%s, low: %s°%s' % (
                            datetime.strptime(fc_weather['date'], '%d %b %Y').strftime('%a %b %d'),
                            fc_weather['text'], fc_weather['high'],
                            units['temperature'], fc_weather['low'], units['temperature'])
        else:  # tomorrow portion
            if date.lower() in ('now', "现在"):
                if userlocale == 'zh_cn':
                    speech = '%s的天气: %s, 温度是华氏%s°%s' % (
                        city, conv_weather_cond(condition['code'], 's_cn'), condition['temp'], units['temperature'])
                elif userlocale in ('zh_tw', 'zh_hk'):
                    speech = '%s的天氣: %s, 溫度是華氏%s°%s' % (
                        city, conv_weather_cond(condition['code'], 's_cn'), condition['temp'], units['temperature'])
                else:
                    speech = 'Current weather in %s: %s, the temperature is %s°%s' % (
                        location['city'], condition['text'],
                        condition['temp'], units['temperature'])
            else:
                if datetime.strptime(date, '%Y-%m-%d') < datetime.strptime(forecast_items[0]['date'], '%d %b %Y'):
                    temp_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=7)
                    date = temp_date.strftime("%Y-%m-%d")
                item_num = -1
                fc_weather = forecast(date, item_num, forecast_items)
                if userlocale == 'zh_cn':
                    speech = '%s的天气(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
                        city, fc_weather['date'], conv_weather_cond(fc_weather['code'], 's_cn'),
                        fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature']
                    )
                elif userlocale in ('zh_tw', 'zh_hk'):
                    speech = '%s的天氣(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
                        city, fc_weather['date'], conv_weather_cond(fc_weather['code'], 't_cn'),
                        fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature']
                    )
                else:
                    speech = 'Weather in %s (%s): %s, high: %s°%s, low: %s°%s' % (
                        location['city'], fc_weather['date'], fc_weather['text'],
                        fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature'])
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather'
        }
    elif action in ('Tour', 'Tour.Tour-fallback'):
        data = []
        payload = ['SEOUL', 'BUSAN', 'TOKYO', 'OSAKA', 'NAGOYA']
        if userlocale == 'zh_cn':
            speech = 'Where are you travelling to? (ex. Seoul, Osaka, or Tokyo)'
            title = ['尔的', '釜山', '东京', '大阪', '名古屋']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = 'Where are you travelling to? (ex. Seoul, Osaka, or Tokyo)'
            title = ['爾的', '釜山', '東京', '大阪', '名古屋']
        else:
            speech = 'Where are you travelling to? (ex. Seoul, Osaka, or Tokyo)'
            title = ['Seoul', 'Busan', 'Tokyo', 'Osaka', 'Nagoya']
        datum = {
            'text': speech,
            'quick_replies': [
                {
                    'content_type': 'text',
                    'title': title[0],
                    'payload': payload[0]
                },
                {
                    'content_type': 'text',
                    'title': title[1],
                    'payload': payload[1]
                },
                {
                    'content_type': 'text',
                    'title': title[2],
                    'payload': payload[2]
                },
                {
                    'content_type': 'text',
                    'title': title[3],
                    'payload': payload[3]
                },
                {
                    'content_type': 'text',
                    'title': title[4],
                    'payload': payload[4]
                }
            ]
        }
        data.append(datum)
        res = {
            'speech': '',
            'displayText': '',
            'source': 'apiai-tour',
            'data': data
        }
        return res
    elif action in ('Tour.location', 'Tour.location.Tour-location-fallback'):
        city = req['result']['parameters'].get('city')

        if userlocale == 'zh_cn':
            button_title = '点击查看'
            speech = '可唔可以介绍%s既必去当地团俾我呀.\n' % city
        elif userlocale in ('zh_tw', 'zh_hk'):
            button_title = '點擊查看'
            speech = '可唔可以介紹%s既必去當地團俾我呀.\n' % city
        else:
            button_title = 'Click to view'
            speech = 'Here are the top recommended tours in %s.\n' % city
        _data = {
            'city': city,
            'lang': userlocale
        }

        tf_res = exapi_travelflan_tour(_data)
        if not tf_res.get('day1'):
            return None
        data = list()
        for day in range(1, len(tf_res) + 1):
            d = tf_res['day%d' % (day,)]
            elements = list()

            for j, day_item in enumerate(d):
                for k, item in enumerate(day_item):
                    if item['locale'].lower() == userlocale:
                        title = item['name']
                        subtitle = item['highlight']
                        image_url = item['photo']
                        link = item['link']

                        fb_item = {
                            'title': 'Tour {}: {}'.format(j + 1, title),
                            'subtitle': subtitle,
                            'image_url': image_url,
                            'buttons': [
                                {
                                    'type': 'web_url',
                                    'url': link,
                                    'title': button_title
                                }
                            ]
                        }

                        elements.append(fb_item)
                        speech += '(%s) %s\n' % (j + 1, title)
                        break

            data_item = {
                'attachment_type': 'template',
                'attachment_payload': {
                    'template_type': 'generic',
                    'elements': elements
                }
            }
            data.append(data_item)

        l = 0
        for x in speech.split('\n'):
            l += len(x)
            if l > 500:
                speech = speech[:l - len(x)] + '\n\n...'
                break

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-tour',
            'data': data
        }
    elif action in ('Itinerary', 'Itinerary.Itinerary-fallback'):
        data = []
        payload = ['SEOUL', 'BUSAN', 'TOKYO', 'OSAKA']
        if userlocale == 'zh_cn':
            speech = 'Where are you going?'
            title = ['尔的', '釜山', '东京', '大阪']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = 'Where are you going?'
            title = ['爾的', '釜山', '東京', '大阪']
        else:
            speech = 'Where are you going?'
            title = ['Seoul', 'Busan', 'Tokyo', 'Osaka']
        datum = {
            'text': speech,
            'quick_replies': [
                {
                    'content_type': 'text',
                    'title': title[0],
                    'payload': payload[0]
                },
                {
                    'content_type': 'text',
                    'title': title[1],
                    'payload': payload[1]
                },
                {
                    'content_type': 'text',
                    'title': title[2],
                    'payload': payload[2]
                },
                {
                    'content_type': 'text',
                    'title': title[3],
                    'payload': payload[3]
                }
            ]
        }
        data.append(datum)
        res = {
            'speech': '',
            'displayText': '',
            'source': 'apiai-itinerary',
            'data': data
        }
        return res
    elif action in ('Itinerary.location', 'Itinerary.location.Itinerary-location-fallback'):
        data = []
        payload = ['5']
        if userlocale == 'zh_cn':
            speech = 'How many days do you want to go?'
            title = ['5']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = 'How many days do you want to go?'
            title = ['5']
        else:
            speech = 'How many days do you want to go?'
            title = ['5']
        datum = {
            'text': speech,
            'quick_replies': [
                {
                    'content_type': 'text',
                    'title': title[0],
                    'payload': payload[0]
                }
            ]
        }
        data.append(datum)
        res = {
            'speech': '',
            'displayText': '',
            'source': 'apiai-itinerary',
            'data': data
        }
        return res
    elif action in ('Itinerary.num_days', 'Itinerary.num_days.Itinerary-num_days-fallback'):
        data = []
        payload = ['GENERAL', 'FOOD', 'SHOPPING', 'KIDS', 'SUBURBS']
        if userlocale == 'zh_cn':
            speech = 'What is the purpose of your travel?'
            title = ['一般', '美食', '购物', '亲子', '近郊']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = 'What is the purpose of your travel?'
            title = ['一般', '美食', '購物', '親子', '近郊']
        else:
            speech = 'What is the purpose of your travel?'
            title = ['General', 'Food', 'Shopping', 'Kids', 'Suburbs']
        datum = {
            'text': speech,
            'quick_replies': [
                {
                    'content_type': 'text',
                    'title': title[0],
                    'payload': payload[0]
                },
                {
                    'content_type': 'text',
                    'title': title[1],
                    'payload': payload[1]
                },
                {
                    'content_type': 'text',
                    'title': title[2],
                    'payload': payload[2]
                },
                {
                    'content_type': 'text',
                    'title': title[3],
                    'payload': payload[3]
                },
                {
                    'content_type': 'text',
                    'title': title[4],
                    'payload': payload[4]
                }
            ]
        }
        data.append(datum)
        res = {
            'speech': '',
            'displayText': '',
            'source': 'apiai-itinerary',
            'data': data
        }
        return res
    elif action in ('Itinerary.theme', 'Itinerary.theme.Itinerary-theme-fallback'):
        city = req['result']['parameters'].get('city')
        num_days = req['result']['parameters'].get('num_days')
        theme = req['result']['parameters'].get('theme')

        if userlocale == 'zh_cn':
            map_title = '地图: %s -> %s'
            button_title = '点击查看'
            speech = '以下是%s天的行程：\n' % num_days
        elif userlocale in ('zh_tw', 'zh_hk'):
            map_title = '地圖: %s -> %s'
            button_title = '點擊查看'
            speech = '以下是%s天的行程：\n' % num_days
        else:
            map_title = 'Map: %s -> %s'
            button_title = 'Click to view'
            speech = 'Here is the %s-day itinerary.\n' % num_days
        _data = {
            'city': city,
            'num_days': num_days,
            'theme': theme,
            'lang': userlocale
        }

        tf_res = exapi_travelflan_itin(_data)
        if not tf_res.get('day1'):
            return None
        data = list()
        for day in range(1, len(tf_res) + 1):
            d = tf_res['day%d' % (day,)]
            elements = list()
            map_data = list()

            if userlocale in ('zh_cn', 'zh_tw', 'zh_hk'):
                map_url = 'http://maps.google.cn/maps?saddr=%s&daddr=%s&dirflg=r'
            else:
                map_url = 'https://www.google.com/maps?saddr=%s&daddr=%s&dirflg=r'

            speech += 'Day {}:\n'.format(day)
            prev_map = None
            for j, day_item in enumerate(d):
                for k, item in enumerate(day_item):
                    if item['locale'].lower() == userlocale:
                        title = item['name']
                        subtitle = item['highlight']
                        image_url = item['photo']
                        link = item['link']

                        fb_item = {
                            'title': 'Day {}-{}: {}'.format(day, j + 1, title),
                            'subtitle': subtitle,
                            'image_url': image_url,
                            'buttons': [
                                {
                                    'type': 'web_url',
                                    'url': link,
                                    'title': button_title
                                }
                            ]
                        }

                        if prev_map:
                            map_item = {
                                'title': 'Day {} {}'.format(day, map_title % (prev_map, title)),
                                'subtitle': '\n',
                                'image_url': MAP_IMAGE_URL,
                                'buttons': [
                                    {
                                        'type': 'web_url',
                                        'url': map_url % (prev_map.replace(' ', '+'), title.replace(' ', '+')),
                                        'title': button_title
                                    }
                                ]
                            }
                            map_data.append(map_item)

                        prev_map = title
                        elements.append(fb_item)
                        speech += '(%s) %s\n' % (j + 1, title)
                        break

            elements += map_data
            data_item = {
                'attachment_type': 'template',
                'attachment_payload': {
                    'template_type': 'generic',
                    'elements': elements
                }
            }
            data.append(data_item)

        l = 0
        for x in speech.split('\n'):
            l += len(x)
            if l > 500:
                speech = speech[:l - len(x)] + '\n\n...'
                break

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-itinerary',
            'data': data
        }
        print(res)
    elif action == 'direction':
        speech, data = parse_json(req)
        print('SPEECH IS \n%s' % (speech))
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation',
            'data': data
        }
    elif action == 'translation':
        print('11111') - 8
        if req['result']['parameters'].get('translation'):
            language = req['result']['parameters']['translation']['language']
        elif req['result']['parameters'].get('language'):
            language = req['result']['parameters']['language']
        else:
            language = req['result']['parameters'].get('prev-language')
        if req['result']['parameters'].get('phrase'):
            phrase = req['result']['parameters']['phrase']
        else:
            phrase = req['result']['parameters'].get('prev-phrase')
        print('22222')
        code = find_language_code(language.lower())
        url = TRANSLATE_BASE_URL + urlencode({'text': phrase, 'to': code, 'authtoken': 'dHJhdmVsZmxhbjp0b3VyMTIzNA=='})
        print('33333')
        print('url = {}'.format(url))
        _res = urlopen(url).read()
        print('12345')
        tmpl = get_response_template(userlocale)
        print('44444')
        language = convert_langauge_to_user_locale(language.lower(), userlocale)
        speech = tmpl % (phrase, language, _res.decode())
        print('55555')
        print('Speech: \n%s' % (speech))
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-translate'
        }
    elif action == 'gurunavi':
        parameters = req['result']['parameters']
        location = parameters.get('address')
        cuisine = parameters.get('gurunavi_cuisine_temp')

        url_cuisine = GURUNAVI_CATEGORY_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
        url_location = GURUNAVI_AREA_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
        res_cuisine = requests.get(url_cuisine).json()['category_l']
        res_location = requests.get(url_location).json()['garea_large']

        for i, item in enumerate(res_location):
            if location.lower() in item.get('areaname_l').lower():
                print('found it')
                print('Location: found code is %s' % (item.get('areacode_l')))
                location_code = item.get('areacode_l')
                break
            else:
                pass
        if not location_code:
            return None

        for i, item in enumerate(res_cuisine):
            if cuisine.lower() in item.get('category_l_name').lower():
                print('found it')
                print('Cuisine: found code is %s' % (item.get('category_l_code')))
                cuisine_code = item.get('category_l_code')
                break
            else:
                pass
        if not cuisine_code:
            return None

        url_lookup = GURUNAVI_SEARCH_URL + urlencode(
            {'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en', 'areacode_l': location_code,
             'category_l': cuisine_code})
        _res = requests.get(url_lookup).json()

        speech = ''

        elements = list()

        if not _res['rest']:
            print("Empty list!")
        else:
            for i, item in enumerate(_res['rest']):
                fb_item = {
                    'title': item['name']['name'],
                    'subtitle': '%s\n%s' % (item['name']['name_sub'], item['contacts']['address']),
                    'image_url': item['image_url']['thumbnail'],
                    'buttons': [
                        {
                            'type': 'web_url',
                            'url': item['url'],
                            'title': 'TEMP BUTTON TITLE'
                        }
                    ]
                }
                elements.append(fb_item)
                if userlocale == 'zh_cn':
                    speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                        i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                        item['contacts']['tel'], item['business_hour']
                    )
                elif userlocale in ('zh_tw', 'zh_hk'):
                    speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                        i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                        item['contacts']['tel'], item['business_hour']
                    )
                else:
                    speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                        i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                        item['contacts']['tel'], item['business_hour']
                    )

                speech += '%s. name: %s\nsummary: %s\naddress: %s\ntel: %s\nbusiness hours: %s\n\n' % (
                    i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                    item['contacts']['tel'], item['business_hour']
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
                    'attachment_payload': {
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
    elif action in ('attraction', 'accommodation', 'restaurant', 'shopping'):
        if userlocale == 'zh_cn':
            lang = '01'
            button_title = '点击查看'
        elif userlocale in ('zh_tw', 'zh_hk'):
            lang = '02'
            button_title = '點擊查看'
        else:
            lang = '04'
            button_title = 'Click to view'

        if action == 'restaurant':
            print('IN RESTAURANT ACTION')
            category1 = '3000'
            if req['result']['parameters'].get('cuisine'):
                cuisine = req['result']['parameters']['cuisine'].lower()
            else:
                cuisine = req['result']['parameters'].get('prev-cuisine').lower()
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
                return None
        elif action == 'attraction':
            category1 = '4000'
            if req['result']['parameters'].get('attraction'):
                attraction = req['result']['parameters']['attraction'].lower()
            else:
                attraction = req['result']['parameters'].get('prev-attraction').lower()
            if attraction == 'historical site' or attraction == '遗址':
                category2 = '4101'
            elif attraction == 'shooting site' or attraction == '拍摄场所':
                category2 = '4102'
            else:
                return None
        elif action == 'accommodation':
            category1 = '2000'
            if req['result']['parameters'].get('accommodation'):
                accommodation = req['result']['parameters']['accommodation'].lower()
            else:
                accommodation = req['result']['parameters'].get('prev-accommodation').lower()
            if accommodation == 'hotel' or accommodation == '饭店':
                category2 = '2101'
            elif accommodation == 'motel' or accommodation == '汽车旅馆':
                category2 = '2102'
            elif accommodation == 'guest house' or accommodation == '背包客栈':
                category2 = '2105'
            elif accommodation == 'bed and breakfast' or accommodation == '民宿':
                category2 = '2106'
            else:
                return None
        elif action == 'shopping':
            category1 = '5000'
            if req['result']['parameters'].get('shopping'):
                shopping = req['result']['parameters']['shopping'].lower()
            else:
                shopping = req['result']['parameters'].get('prev-shopping').lower()
            if shopping == 'duty-free':
                category2 = '5101'
            elif shopping == 'department store':
                category2 = '5102'
            elif shopping == 'shopping district':
                category2 = '5103'
            elif shopping == 'accessories':
                category2 = '5104'
            elif shopping == 'fashion':
                category2 = '5105'
            elif shopping == 'high-end':
                category2 = '5106'
            elif shopping == 'sports':
                category2 = '5107'
            elif shopping == 'underwear':
                category2 = '5108'
            elif shopping == 'kids':
                category2 = '5109'
            elif shopping == 'jewellery':
                category2 = '5110'
            elif shopping == 'cosmetics':
                category2 = '5111'
            elif shopping == 'electronics':
                category2 = '5112'
            elif shopping == 'optics':
                category2 = '5113'
            elif shopping == 'specialty':
                category2 = '5114'
            elif shopping == 'shoes':
                category2 = '5115'
            elif shopping == 'retailer':
                category2 = '5116'
            elif shopping == 'market':
                category2 = '5117'
            elif shopping == 'shopping center':
                category2 = '5118'
            elif shopping == 'outlet':
                category2 = '5119'
            elif shopping == 'mall':
                category2 = '5120'
            else:
                return None
        else:
            category1 = None
        if req['result']['parameters'].get('address'):
            address = req['result']['parameters']['address']
        else:
            address = req['result']['parameters']['prev-address']

        geocode_result = gmaps.geocode(address)
        latitude = geocode_result[0]['geometry']['location']['lat']
        longitude = geocode_result[0]['geometry']['location']['lng']
        _data = {
            'lang': lang,
            'category1': category1,
            'category2': category2,
            # 'cityCode': None,
            # 'areaCode': None,
            'latitude': str(latitude),
            'longitude': str(longitude),
            'distance': '10000'
        }
        _res = exapi_pengtai(_data)

        speech = ''

        elements = list()
        if not _res['list']:
            speech = ''
            print("speech is empty")
        else:
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
                print('elements:::::::\n%s' % elements)
                11111111111
            l = 0
            for x in speech.split('\n'):
                l += len(x)
                if l > 500:
                    speech = speech[:l - len(x)] + '\n\n...'
                    break

        data = [
            {
                'attachment_type': 'template',
                'attachment_payload': {
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
    elif action == 'restaurant.init':
        speech = "How can I help you?"
        res = {
            'speech': speech,
            'displayText': '',
            'source': 'apiai-restaurant',
            'data': ''
        }
    elif action in ('Restaurant.Restaurant-fallback'):
        print('IN Restaurant.Restaurant-fallback ACTION')
        data = []
        payload = ['SOUTH KOREA', 'JAPAN', 'OTHER']
        if userlocale == 'zh_cn':
            speech = '您要去哪个国家？'
            title = ['韩国', '日本', '其他']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '您要去哪個國家？'
            title = ['韓國', '日本', '其他']
        else:
            speech = 'What country are you travelling to?'
            title = ['South Korea', 'Japan', 'Other']
        datum = {
            'text': speech,
            'quick_replies': [
                {
                    'content_type': 'text',
                    'title': title[0],
                    'payload': payload[0]
                },
                {
                    'content_type': 'text',
                    'title': title[1],
                    'payload': payload[1]
                },
                {
                    'content_type': 'text',
                    'title': title[2],
                    'payload': payload[2]
                }
            ]
        }
        data.append(datum)
        res = {
            'speech': speech,
            'displayText': '',
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
