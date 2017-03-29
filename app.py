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

PENGTAI_URL = 'http://www.hanguoing.cn/exApi/travelFlan'
PENGTAI_TEST_URL = 'http://test1.hanguoing.com/exApi/travelFlan'
PENGTAI_KEY = 'xmvoqpfvmffosqksrkqtmqslek'

GURUNAVI_URL = 'https://api.gnavi.co.jp/ForeignRestSearchAPI/20150630/?'
GURUNAVI_KEY = '6d98dbe7eca799250d844be0426a3bad'
GURUNAVI_AREA_URL = 'https://api.gnavi.co.jp/master/GAreaLargeSearchAPI/20150630/?'
GURUNAVI_CATEGORY_URL = 'https://api.gnavi.co.jp/master/CategoryLargeSearchAPI/20150630/?'


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
    print('123')
    lang = req['originalRequest']['data'].get('locale')
    if lang == 'zh_CN':
        dir_file = DIR_FILE_CN
    elif lang in ('zh_TW', 'zh_HK'):
        dir_file = DIR_FILE_TW
    else:
        dir_file = DIR_FILE_EN

    result = req.get('result')
    parameters = result.get('parameters')

    print('1. {}'.format(parameters.get('address-from')))
    print('2. {}'.format(parameters.get('prev-address-from')))
    print('3. {}'.format(parameters.get('address-to')))
    print('4. {}'.format(parameters.get('prev-address-to')))

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


def exapi_pengtai(data):
    timestamp = str(int(time.time()))
    plain = '%s|%s' % (PENGTAI_KEY, timestamp)
    headers = {'X-hash': hashlib.sha256(plain.encode('utf-8')).hexdigest()}

    data['timestamp'] = timestamp

    try:
        res = requests.get(PENGTAI_TEST_URL, headers=headers, params=data)
        return res.json()
    except Exception as e:
        print(e)
        return None


def process_request(req):
    res = None
    try:
        userlocale = req['originalRequest']['data']['locale'].lower()
    except Exception as e:
        userlocale = 'zh_cn'
    print('req is {}'.format(req))
    action = req['result']['action']
    print('action1 is {}'.format(action))
    if action == 'prev_context':
        print('in context area')
        print('parameters: {}'.format(req['result'].get('parameters')))
        print('action2 is {}'.format(req['result']['parameters'].get('prev-action')))
        action = req['result']['parameters'].get('prev-action')
        print('123123')
        if req['result']['parameters'].get('city'):
            print('aaaaaa')
            city = req['result']['parameters']['city']
            print('cccccc')
        elif not req['result']['parameters'].get('city') and req['result']['parameters'].get('prev-city'):
            print('dddddd')
            city = req['result']['parameters'].get('prev-city')
            print('eeeeee')
        else:
            None
    else:
        if req['result']['parameters'].get('city'):
            city = req['result']['parameters'].get('city')
    print('action3 is {}'.format(action))

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
                    speech = '%s的天气: %s, 温度是华氏%s°%s' % (city, temp, condition['temp'], units['temperature'])
                elif userlocale in ('zh_tw', 'zh_hk'):
                    temp = conv_weather_cond(condition['code'], 't_cn')
                    speech = '%s的天氣: %s, 溫度是華氏%s°%s' % (city, temp, condition['temp'], units['temperature'])
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
    elif action == 'direction':
        print("yes here")
        speech, data = parse_json(req)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation',
            'data': data
        }
    elif action == 'translation':
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
        code = find_language_code(language.lower())
        url = TRANSLATE_BASE_URL + urlencode({'text': phrase, 'to': code, 'authtoken': 'dHJhdmVsZmxhbjp0b3VyMTIzNA=='})
        _res = urlopen(url).read()
        tmpl = get_response_template(userlocale)
        language = convert_langauge_to_user_locale(language.lower(), userlocale)
        speech = tmpl % (phrase, language, _res.decode())
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
        print('location is %s'%(location))
        print('cuisine is %s' %(cuisine))

        url_cuisine = GURUNAVI_CATEGORY_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
        url_location = GURUNAVI_AREA_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
        res_cuisine = requests.get(url_cuisine).json()['category_l']
        res_location = requests.get(url_location).json()['garea_large']

        for i, item in enumerate(res_cuisine):
            if cuisine == item.get('category_l_name').lower():
                print('found it')
                print('Cuisine: found code is %s' % (item.get('category_l_code')))
                cuisine_code = item.get('category_l_code')
            else:
                return None
        for i, item in enumerate(res_location):
            print('item')
            if location.lower() == item.get('areaname_l').lower():
                print('found it')
                print('Location: found code is %s' % (item.get('areacode_l')))
                location_code = item.get('areacode_l')
            else:
                return None


        # print('res_cuisine: \n%s' % (res_cuisine))
        # print('res_location: \n%s' % (res_location))





        #url = GURUNAVI_URL + urlencode({'keyid': GURUNAVI_KEY, 'format':'json','lang':'en','areacode_l':area_code,'category_l':category_code})

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
