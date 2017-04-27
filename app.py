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

TF_ITINERARY_URL = 'https://flanb-demo.travelflan.com/data/itinerary?type=0&'
TF_TOUR_URL = 'https://flanb-demo.travelflan.com/data/itinerary?type=1&days=1&'

TF_DATA_URL = 'https://flanb-demo.travelflan.com/data?page_size=10&dist=3000&point=%s,%s&main_category=1'
TF_DATA_TOKEN = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6MSwidXNlcm5hbWUiOiI3MjJmNTM0NTVjOGM0ZTI0OGIwNzI4OWVmY2IwYjM2ZiIsImlzX3N1cGVydXNlciI6dHJ1ZSwiaXNfc3RhZmYiOnRydWUsImlzX2FjdGl2ZSI6dHJ1ZSwicHJvdmlkZXIiOjEsImV4cCI6MTUyNDUyNTA2NCwiaXNzIjoiVHJhdmVsRmxhbiJ9.T6KTfCUj9THsud0NazTFKmbKolOUDgqvWG9q66R_wDc'

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

RESTAURANT_LOCATION_KO = ('Seoul', '서울', '首尔', '首爾',
                          'Myeongdong', '명동', '明洞', 'Myeong-dong', 'Myungdong',
                          'Dongdaemun', '동대문', '东大门', '東大門', 'Dongdaemoon',
                          'Incheon', '인천', '仁川',
                          'Pusan', '부산', '釜山', 'Busan',
                          'Itaewon', '이태원',
                          'Gangnam', '강남', '江南',
                          'Apgujeong', '압구정', '狎鸥亭', '狎鷗亭',
                          'Sinsa', '신사', '新沙')
RESTAURANT_LOCATION_JP = ('Tokyo', '도쿄', '东京', '東京',
                          'Osaka', '오사카', '大阪',
                          'Kyoto', '교토', '京都',
                          'Kobe', '고베', '神戶',
                          'Nara', '나라', '奈良',
                          'Uji', '우지', '宇治',
                          'Shinjuku', '신주쿠', '新宿',
                          'Nagoya', '나고야', '名古屋')

RESTAURANT_CUISINE_KOREAN = ('Korean', '韩式', '韩食', '韓式', '韓食', '韩国', '韓國', '韓餐', '烤肉')
RESTAURANT_CUISINE_JAPANESE = ('Japanese', '日式', '日食', '日本', '和食')
RESTAURANT_CUISINE_CHINESE = ('Chinese', '中式', '中食', '中国', '中國', '中餐', '唐餐')
RESTAURANT_CUISINE_WESTERN = ('Western', '西餐', '西式', '歐美', '各國', '美式', '意大利餐')
RESTAURANT_CUISINE_FOREIGN = ('Foreign', '异国', '異國', '亞洲', '多國', '泰國餐')
RESTAURANT_CUISINE_CAFFE = ('Caffe', 'Coffee', '咖啡')
RESTAURANT_CUISINE_FASTFOOD = ('Fastfood', '速食', '小點', '快餐', '小食', '小吃', '小点', 'Quick Bite')
RESTAURANT_CUISINE_PUB = ('Pub', '酒', 'Lounge', 'Bar', 'Beer')
RESTAURANT_CUISINE_SEAFOOD = ('Seafood', 'Sushi', '寿司', '鱼类料理', '海鲜', '壽司', '魚類料理', '海鮮')
RESTAURANT_CUISINE_ITALIAN = ('Italian', '意大利菜', '義大利式')
RESTAURANT_CUISINE_FRENCH = ('French', '法式', '法国菜')
RESTAURANT_CUISINE_ORGANIC = ('Organic', '有机菜', '有機')
RESTAURANT_CUISINE_BREAD = ('Bread', '甜点', '甜點')
RESTAURANT_CUISINE_YAKINIKU = ('Yakiniku', '烤肉', '烤内脏', '燒肉', '烤內臟')
RESTAURANT_CUISINE_IZAKAYA = ('Izakaya', '居酒屋')
RESTAURANT_CUISINE_NOODLE = ('Noodle', '面类', '拉面', '荞麦面', '乌冬面等', '麵類', '拉麵', '蕎麥麵', '烏冬麵等')


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


def make_yql_query(city):
    return 'select * from weather.forecast ' \
           'where woeid in (select woeid from geo.places(1) where text=\'%s\') and u=\'c\'' % (city,)


def get_weather_data(city):
    url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(city), 'format': 'json'})
    print('YQL-Request:\n%s' % (url,))
    _res = urlopen(url).read()
    print('YQL-Response:\n%s' % (_res,))

    data = json.loads(_res)

    if 'query' not in data:
        return None
    if 'results' not in data['query']:
        return None
    if 'channel' not in data['query']['results']:
        return None
    for x in ('location', 'item', 'units'):
        if x not in data['query']['results']['channel']:
            return None
    if 'forecast' not in data['query']['results']['channel']['item']:
        return None

    location = data['query']['results']['channel']['location']['city']
    units = data['query']['results']['channel']['units']
    forecast_items = data['query']['results']['channel']['item']['forecast']

    res = {
        'location': location,
        'units': units,
        'forecast_items': forecast_items
    }

    return res


def weather_speech(request_data):
    # request_data
    city = request_data.get('city')
    date = request_data.get('date')
    isForecast = request_data.get('isForecast')
    if not isForecast:
        isForecast = False
    elif isForecast in ('True', 'true', 'TRUE', 'Yes', 'yes', 'YES', 'y', 'Y'):
        isForecast = True
    else:
        isForecast = False
    language = request_data['language']

    weather_data = get_weather_data(city)
    unit = weather_data['units']['temperature']
    forecast_items = weather_data['forecast_items']

    if not city:
        # ask for city
        if language == 'zh_cn':
            speech = '您想查询哪里的天气呢？ (如：首尔/东京/上海等)'
        elif language in ('zh_tw', 'zh_hk'):
            speech = '您想查詢哪裡的天氣呢？ (如：首爾/東京/上海等)'
        else:
            speech = 'Where do you want to know about the weather? (Ex. Seoul, Tokyo, Shanghai)'
    else:
        if isForecast is True:
            # 10-day forecast
            if language == 'zh_cn':
                speech = '%s天氣預報(10天):' % city
            elif language in ('zh_tw', 'zh_hk'):
                speech = '%s天气预报(10天):' % city
            else:
                speech = 'Here is the 10-day forecast for %s:' % city

            for item in forecast_items:
                condition_code = item['code']
                high = item['high']
                low = item['low']
                condition = item['text']
                date = item['date']

                if language in ('zh_cn', 'zh_tw', 'zh_hk'):
                    if language == 'zh_cn':
                        condition = conv_weather_cond(condition_code, 's_cn')
                    else:
                        condition = conv_weather_cond(condition_code, 't_cn')
                    speech += '\n(%s) 高溫: %s°%s, 低溫: %s°%s, %s' % (
                        datetime.strptime(date, '%d %b %Y').strftime('%m/%d'),
                        high, unit, low, unit, condition)
                else:
                    speech += '\n(%s) high: %s°%s, low: %s°%s, %s' % (
                        datetime.strptime(date, '%d %b %Y').strftime('%m/%d'),
                        high, unit, low, unit, condition)
        else:
            if not date:
                # current weather
                print("DISPLAY CURRENT WEATHER")

            else:
                # weather by date
                date_found = False
                for item in forecast_items:
                    if datetime.strptime(date, '%Y/%m/%d').strftime('%d %b %Y') in item['date']:
                        date_found = True
                        condition_code = item['code']
                        high = item['high']
                        low = item['low']
                        condition = item['text']
                        break

                if date_found is False:
                    return None

                if language == 'zh_cn':
                    title = ['是', '否']
                    speech = '%s的天气(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
                        city, date, conv_weather_cond(condition_code, 's_cn'),
                        high, unit, low, unit)
                    print('Speech is {}'.format(speech))
                elif language in ('zh_tw', 'zh_hk'):
                    title = ['是', '否']
                    speech = '%s的天气(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
                        city, date, conv_weather_cond(condition_code, 't_cn'),
                        high, unit, low, unit)
                else:
                    title = ['Yes', 'No']
                    speech = 'Weather in %s (%s): %s, high: %s°%s, low: %s°%s' % (
                        city, date, condition,
                        high, unit, low, unit)

    # if isForecast is False:
    #
    # else:
    #     print('Forecast is True')

    return speech


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
    print('from_loc = %s' % (from_loc,))
    print('to_loc = %s' % (to_loc,))
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

        speech = ''
        if lang == 'zh_TW' or lang == 'zh_HK':
            if fare:
                speech += '費用: %s\n' % (fare,)
            if departure_time:
                speech += '出發時間: %s\n' % (departure_time,)
            if arrival_time:
                speech += '抵達時間: %s\n' % (arrival_time,)
            if distance:
                speech += '距離: %s\n' % (distance,)
            if duration:
                speech += '所需時間: %s\n\n' % (duration,)
            if route:
                speech += '路線:\n%s' % (route,)
        elif lang == 'zh_CN':
            if fare:
                speech += '费用: %s\n' % (fare,)
            if departure_time:
                speech += '出发时间: %s\n' % (departure_time,)
            if arrival_time:
                speech += '抵达时间: %s\n' % (arrival_time,)
            if distance:
                speech += '距离: %s\n' % (distance,)
            if duration:
                speech += '所需时间: %s\n\n' % (duration,)
            if route:
                speech += '路线:\n%s' % (route,)
        else:
            if fare:
                speech += 'Fare: %s\n' % (fare,)
            if departure_time:
                speech += 'Departure Time: %s\n' % (departure_time,)
            if arrival_time:
                speech += 'Arrival Time: %s\n' % (arrival_time,)
            if distance:
                speech += 'Distance: %s\n' % (distance,)
            if duration:
                speech += 'Duration: %s\n\n' % (duration,)
            if route:
                speech += 'Route:\n%s' % (route,)

        l = 0
        for x in speech.split('\n'):
            l += len(x)
            if l > 500:
                speech = speech[:l - len(x)] + '\n\n...'
                break
    else:
        speech = ''

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
        print('1. BEFORE: from_loc = {}'.format(from_loc))
        if 'please' in from_loc.lower():
            from_loc = from_loc.rsplit(' ', 1)[0]
            print('1. AFTER: from_loc = {}'.format(from_loc))
    else:
        from_loc = parameters.get('prev-address-from')

    if parameters.get('address-to'):
        to_loc = parameters.get('address-to')
        print('2. BEFORE: to_loc = {}'.format(to_loc))
        if 'please' in to_loc.lower():
            to_loc = to_loc.rsplit(' ', 1)[0]
            print('2. AFTER: to_loc = {}'.format(to_loc))
    else:
        to_loc = parameters.get('prev-address-to')

    speech, data = grab_answer(from_loc, to_loc, dir_file, lang)
    if not speech:
        speech, data = get_gmap_directions(from_loc, to_loc, lang)
    return speech, data


def exapi_travelflan_itin(data):
    if data['theme'] in ('Food Lover', '美食'):
        theme = 1
    elif data['theme'] in ('Shopping', '逛街購物', '逛街购物'):
        theme = 2
    elif data['theme'] in ('with Kids', '亲子', '親子'):
        theme = 3
    else:
        theme = 0

    if data['city'] == 'Tokyo' and theme == 1:  # TODO: Tmp
        theme = 0

    itinerary_url = TF_ITINERARY_URL + urlencode({'area': data['city'],
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

    print('**********************************************')
    print('Pengtai data: {}'.format(data))

    try:
        res = requests.get(PENGTAI_TEST_URL, headers=headers, params=data)
        print(res.json())
        return res.json()
    except Exception as e:
        print(e)
        return None


def exapi_gurunavi_ex(location, cuisine, lang):
    url_cuisine = GURUNAVI_CATEGORY_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
    url_location = GURUNAVI_AREA_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
    res_cuisine = requests.get(url_cuisine).json()['category_l']
    res_location = requests.get(url_location).json()['garea_large']

    location_code = None
    for i, item in enumerate(res_location):
        if location.lower() in item.get('areaname_l').lower():
            print('Location: found code is %s' % (item.get('areacode_l')))
            location_code = item.get('areacode_l')
            break
    if not location_code:
        return None

    cuisine_code = None
    for i, item in enumerate(res_cuisine):
        if cuisine.lower() in item.get('category_l_name').lower():
            print('Cuisine: found code is %s' % (item.get('category_l_code')))
            cuisine_code = item.get('category_l_code')
            break
    if not cuisine_code:
        return None

    if lang == 'zh_hk':
        lang == 'zh_tw'
    elif lang == 'en_us':
        lang = 'en'

    url_lookup = GURUNAVI_SEARCH_URL + urlencode(
        {'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': lang,
         'areacode_l': location_code, 'category_l': cuisine_code})
    return requests.get(url_lookup).json()


def exapi_gurunavi(data):
    print("In exapi_gurunavi(data) **********")

    lang = ''
    if data['lang'].lower() == 'zh_hk':
        lang = 'zh_tw'
    elif data['lang'].lower() == 'en_us':
        lang = 'en'
    else:
        lang = 'zh_cn'

    url_lookup = GURUNAVI_SEARCH_URL + urlencode({
        'keyid': GURUNAVI_KEY,
        'format': data['format'],
        'category_l': data['category_l'],
        'latitude': data['latitude'],
        'longitude': data['longitude'],
        'input_coordinates_mode': data['input_coordinates_mode'],
        'range': '3',
        'lang': lang
    })

    print('URL: {}'.format(url_lookup))
    _res = requests.get(url_lookup).json()
    return _res


def exapi_gurunavi_category_l(cuisine):
    print('CUISINE WE ARE LOOKING IS {}'.format(cuisine))
    url_cuisine = GURUNAVI_CATEGORY_URL + urlencode({'keyid': GURUNAVI_KEY, 'format': 'json', 'lang': 'en'})
    res_cuisine = requests.get(url_cuisine).json()['category_l']
    category_l_code = None
    if cuisine.lower() == 'japanese':
        cuisine = 'traditional japanese'
    for i, item in enumerate(res_cuisine):
        print('MATCHING: {}'.format(item.get('category_l_name').lower()))
        if cuisine.lower() in item.get('category_l_name').lower():
            print('Cuisine: found code is %s' % (item.get('category_l_code')))
            category_l_code = item.get('category_l_code')
            break
    return category_l_code


def make_quick_replies(locale):
    if locale == 'zh_cn':
        text = '那么有其他可以为您服务的吗?'
        title = ['行程', '一天团', '餐厅', '方向', '天气', '餐厅2']
    elif locale in ('zh_tw', 'zh_hk'):
        text = '那麼有其他可以為您服務的嗎?'
        title = ['行程', '一天團', '餐廳', '方向', '天氣', '餐廳2']
    else:
        text = 'Anything else?'
        title = ['Itinerary', 'Tour', 'Restaurant', 'Transportation', 'Weather', 'Restaurant2']
    return {
        'text': text,
        'quick_replies': [
            {
                'content_type': 'text',
                'title': title[0],
                'payload': 'ITINERARY'
            },
            {
                'content_type': 'text',
                'title': title[1],
                'payload': 'TOUR'
            },
            {
                'content_type': 'text',
                'title': title[2],
                'payload': 'RESTAURANT'
            },
            {
                'content_type': 'text',
                'title': title[3],
                'payload': 'TRANSPORTATION'
            },
            {
                'content_type': 'text',
                'title': title[4],
                'payload': 'WEATHER'
            },
            {
                'content_type': 'text',
                'title': title[5],
                'payload': 'RESTAURANT2'
            },
        ]
    }


def process_request(req):
    res = None
    try:
        userlocale = req['originalRequest']['data']['locale'].lower()
    except Exception as e:
        userlocale = 'zh_cn'
    action = req['result']['action']
    print('action is {}'.format(action))
    # if action == 'prev_context':
    #     action = req['result']['parameters'].get('prev-action')
    #     if req['result']['parameters'].get('city'):
    #         city = req['result']['parameters']['city']
    #     elif not req['result']['parameters'].get('city') and req['result']['parameters'].get('prev-city'):
    #         city = req['result']['parameters'].get('prev-city')
    #     else:
    #         pass
    # else:
    #     if req['result']['parameters'].get('city'):
    #         city = req['result']['parameters'].get('city')
    #
    # if action == 'weather':
    #     url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(city)}) + '&format=json'
    #     print('YQL-Request:\n%s' % (url,))
    #     _res = urlopen(url).read()
    #     print('YQL-Response:\n%s' % (_res,))
    #
    #     data = json.loads(_res)
    #
    #     if 'query' not in data:
    #         return res
    #     if 'results' not in data['query']:
    #         return res
    #     if 'channel' not in data['query']['results']:
    #         return res
    #
    #     for x in ('location', 'item', 'units'):
    #         if x not in data['query']['results']['channel']:
    #             return res
    #
    #     if 'condition' not in data['query']['results']['channel']['item']:
    #         return res
    #     location = data['query']['results']['channel']['location']
    #     condition = data['query']['results']['channel']['item']['condition']
    #     units = data['query']['results']['channel']['units']
    #     forecast_items = data['query']['results']['channel']['item']['forecast']
    #     date = req['result']['parameters'].get('date')
    #     prev_date = req['result']['parameters'].get('prev-date')
    #     date_period = req['result']['parameters'].get('date-period')
    #     prev_dp = req['result']['parameters'].get('prev-dp')
    #     if prev_dp and not date:
    #         date_period = prev_dp
    #     if prev_date and not date_period:
    #         date = prev_date
    #     if not date or (date and date_period):
    #         # current weather
    #         if not date_period:
    #             if userlocale == 'zh_cn':
    #                 temp = conv_weather_cond(condition['code'], 's_cn')
    #                 speech = '%s的天气: %s, 温度是%s°%s' % (city, temp, condition['temp'], units['temperature'])
    #             elif userlocale in ('zh_tw', 'zh_hk'):
    #                 temp = conv_weather_cond(condition['code'], 't_cn')
    #                 speech = '%s的天氣: %s, 溫度是%s°%s' % (city, temp, condition['temp'], units['temperature'])
    #             else:
    #                 speech = 'Current weather in %s: %s, the temperature is %s°%s' % (
    #                     location['city'], condition['text'],
    #                     condition['temp'], units['temperature'])
    #         # 10-day weather forecast
    #         else:
    #             check_date1 = date_period.partition('/')[0]
    #             check_date2 = date_period.partition('/')[2]
    #             check_date1 = datetime.strptime(check_date1, '%Y-%m-%d')
    #             check_date2 = datetime.strptime(check_date2, '%Y-%m-%d')
    #             if check_date1 > datetime.strptime(forecast_items[9]['date'],
    #                                                '%d %b %Y') or check_date2 < datetime.strptime(
    #                 forecast_items[0]['date'], '%d %b %Y'):
    #                 return None
    #
    #             if userlocale == 'zh_cn':
    #                 speech = ('%s天氣預報(10天):' % city)
    #             elif userlocale in ('zh_tw', 'zh_hk'):
    #                 speech = ('%s天气预报(10天):' % city)
    #             else:
    #                 speech = ('Here is the 10-day forecast for %s:' % (location['city']))
    #
    #             for i in range(0, 10):
    #                 item_num = i
    #                 fc_weather = forecast(date, item_num, forecast_items)
    #                 if fc_weather == None:
    #                     speech = None
    #                     break
    #                 if userlocale in ('zh_cn', 'zh_tw', 'zh_hk'):
    #                     if userlocale == 'zh_cn':
    #                         lang = 's_cn'
    #                     else:
    #                         lang = 't_cn'
    #                     w_cond = conv_weather_cond(fc_weather['code'], lang)
    #                     speech += '\n(%s) %s, 高溫: %s°%s, 低溫: %s°%s' % (
    #                         datetime.strptime(fc_weather['date'], '%d %b %Y').strftime('%m/%d'), w_cond,
    #                         fc_weather['high'], units['temperature'],
    #                         fc_weather['low'], units['temperature'])
    #                 else:
    #                     speech += '\n(%s) %s, high: %s°%s, low: %s°%s' % (
    #                         datetime.strptime(fc_weather['date'], '%d %b %Y').strftime('%a %b %d'),
    #                         fc_weather['text'], fc_weather['high'],
    #                         units['temperature'], fc_weather['low'], units['temperature'])
    #     else:  # tomorrow portion
    #         if date.lower() in ('now', "现在"):
    #             if userlocale == 'zh_cn':
    #                 speech = '%s的天气: %s, 温度是华氏%s°%s' % (
    #                     city, conv_weather_cond(condition['code'], 's_cn'), condition['temp'], units['temperature'])
    #             elif userlocale in ('zh_tw', 'zh_hk'):
    #                 speech = '%s的天氣: %s, 溫度是華氏%s°%s' % (
    #                     city, conv_weather_cond(condition['code'], 's_cn'), condition['temp'], units['temperature'])
    #             else:
    #                 speech = 'Current weather in %s: %s, the temperature is %s°%s' % (
    #                     location['city'], condition['text'],
    #                     condition['temp'], units['temperature'])
    #         else:
    #             if datetime.strptime(date, '%Y-%m-%d') < datetime.strptime(forecast_items[0]['date'], '%d %b %Y'):
    #                 temp_date = datetime.strptime(date, '%Y-%m-%d') + timedelta(days=7)
    #                 date = temp_date.strftime("%Y-%m-%d")
    #             item_num = -1
    #             fc_weather = forecast(date, item_num, forecast_items)
    #             if userlocale == 'zh_cn':
    #                 speech = '%s的天气(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
    #                     city, fc_weather['date'], conv_weather_cond(fc_weather['code'], 's_cn'),
    #                     fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature']
    #                 )
    #             elif userlocale in ('zh_tw', 'zh_hk'):
    #                 speech = '%s的天氣(%s): %s, 高溫: %s°%s, 低溫: %s°%s' % (
    #                     city, fc_weather['date'], conv_weather_cond(fc_weather['code'], 't_cn'),
    #                     fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature']
    #                 )
    #             else:
    #                 speech = 'Weather in %s (%s): %s, high: %s°%s, low: %s°%s' % (
    #                     location['city'], fc_weather['date'], fc_weather['text'],
    #                     fc_weather['high'], units['temperature'], fc_weather['low'], units['temperature'])
    #     res = {
    #         'speech': speech,
    #         'displayText': speech,
    #         'source': 'apiai-weather'
    #     }
    if action in ('Reset',):
        data = []
        datum = make_quick_replies(userlocale)
        data.append(datum)
        res = {
            'speech': '',
            'displayText': '',
            'source': 'apiai-transportation',
            'data': data
        }
    elif action in ('Weather', 'Weather.Weather-fallback'):
        # if userlocale == 'zh_cn':
        #     speech = '您想查询哪里的天气呢？ (如：首尔/东京/上海等)'
        # elif userlocale in ('zh_tw', 'zh_hk'):
        #     speech = '您想查詢哪裡的天氣呢？ (如：首爾/東京/上海等)'
        # else:
        #     speech = 'Where do you want to know about the weather? (Ex. Seoul, Tokyo, Shanghai)'
        request_data = {
            'language': userlocale
        }

        speech = weather_speech(request_data)
        if speech is None:
            return None

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather'
        }
    elif action in ('Weather.location', 'Weather.location.Weather-location-fallback'):
        city = req['result']['parameters'].get('city')
        url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(city)}) + '&format=json'
        print('YQL-Request:\n%s' % (url,))
        _res = urlopen(url).read()
        print('YQL-Response:\n%s' % (_res,))

        data = json.loads(_res)

        if 'query' not in data:
            return None
        if 'results' not in data['query']:
            return None
        if 'channel' not in data['query']['results']:
            return None
        for x in ('location', 'item', 'units'):
            if x not in data['query']['results']['channel']:
                return None
        if 'condition' not in data['query']['results']['channel']['item']:
            return None

        location = data['query']['results']['channel']['location']
        condition = data['query']['results']['channel']['item']['condition']
        units = data['query']['results']['channel']['units']

        payload = ['YES', 'NO']
        if userlocale == 'zh_cn':
            title = ['是', '否']
            temp = conv_weather_cond(condition['code'], 's_cn')
            speech = '%s的天气: %s, 温度是%s°%s\n请问您需要天气预报吗?' % (city, temp, condition['temp'], units['temperature'])
        elif userlocale in ('zh_tw', 'zh_hk'):
            title = ['是', '否']
            temp = conv_weather_cond(condition['code'], 't_cn')
            speech = '%s的天氣: %s, 溫度是%s°%s\n請問您需要天氣預報嗎?' % (city, temp, condition['temp'], units['temperature'])
        else:
            title = ['Yes', 'No']
            speech = 'Current weather in %s: %s, the temperature is %s°%s\nWould you like a 10-day forecast?' % (
                location['city'], condition['text'],
                condition['temp'], units['temperature'])

        data = []
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
                }
            ]
        }
        data.append(datum)
        res = {
            'speech': '',
            'displayText': '',
            'source': 'apiai-weather',
            'data': data
        }
    elif action in ('Weather.forecast', 'Weather.forecast.Weather-forecast-fallback'):
        city = req['result']['parameters'].get('city')
        yesno = req['result']['parameters'].get('yesno')
        if yesno == 'No':
            return None
        url = YAHOO_YQL_BASE_URL + urlencode({'q': make_yql_query(city)}) + '&format=json'
        print('YQL-Request:\n%s' % (url,))
        _res = urlopen(url).read()
        print('YQL-Response:\n%s' % (_res,))

        data = json.loads(_res)

        if 'query' not in data:
            return None
        if 'results' not in data['query']:
            return None
        if 'channel' not in data['query']['results']:
            return None
        for x in ('location', 'item', 'units'):
            if x not in data['query']['results']['channel']:
                return None
        if 'forecast' not in data['query']['results']['channel']['item']:
            return None

        location = data['query']['results']['channel']['location']
        units = data['query']['results']['channel']['units']
        forecast_items = data['query']['results']['channel']['item']['forecast']

        if userlocale == 'zh_cn':
            speech = '%s天氣預報(10天):' % city
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '%s天气预报(10天):' % city
        else:
            speech = 'Here is the 10-day forecast for %s:' % (location['city'])

        for i in range(0, 10):
            item_num = i
            fc_weather = forecast(datetime.now().strftime('%Y-%m-%d'), item_num, forecast_items)
            if not fc_weather:
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

        data = []
        datum = make_quick_replies(userlocale)
        data.append(datum)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-weather',
            'data': data
        }
    elif action in ('Tour', 'Tour.Tour-fallback'):
        data = []
        payload = ['SEOUL', 'BUSAN', 'TOKYO', 'OSAKA', 'NAGOYA']
        if userlocale == 'zh_cn':
            speech = '请问您要去哪里旅游呢？ (如：首尔/大阪/东京)'
            title = ['首尔', '釜山', '东京', '大阪', '名古屋']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '請問您要去哪裡旅遊呢？ (如：首爾/大阪/東京)'
            title = ['首爾', '釜山', '東京', '大阪', '名古屋']
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
    elif action in ('Tour.location', 'Tour.location.Tour-location-fallback'):
        city = req['result']['parameters'].get('city')

        if userlocale == 'zh_cn':
            button_title = '点击查看'
            speech = '可唔可以介绍%s既必去当地团俾我呀.\n' % city
            locale = 'zh_CN'
        elif userlocale in ('zh_tw', 'zh_hk'):
            button_title = '點擊查看'
            speech = '可唔可以介紹%s既必去當地團俾我呀.\n' % city
            locale = 'zh_HK'
        else:
            button_title = 'Click to view'
            speech = 'Here are the top recommended tours in %s.\n' % city
            locale = 'en_US'
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

            for k, day_item in enumerate(d, 1):
                item = day_item.get(locale)

                title = item['name']
                subtitle = item['brief']
                image_url = item['image_url']
                url = item['basic_url']

                fb_item = {
                    'title': 'Tour {}: {}'.format(k, title),
                    'subtitle': subtitle,
                    'image_url': image_url,
                    'buttons': [
                        {
                            'type': 'web_url',
                            'url': url,
                            'title': button_title
                        }
                    ]
                }

                elements.append(fb_item)
                speech += '(%s) %s\n' % (k, title)

            data_item = {
                'attachment_type': 'template',
                'attachment_payload': {
                    'template_type': 'generic',
                    'elements': elements
                }
            }
            data.append(data_item)

        datum = make_quick_replies(userlocale)
        data.append(datum)

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
        payload = ['SEOUL', 'TOKYO', 'OSAKA']
        if userlocale == 'zh_cn':
            speech = '请问您要去哪里旅游呢？ (如：首尔/东京/大阪)'
            title = ['首尔', '东京', '大阪']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '請問您要去哪裡旅遊呢？ (如：首爾/東京/大阪)'
            title = ['首爾', '東京', '大阪']
        else:
            speech = 'Where are you going?'
            title = ['Seoul', 'Tokyo', 'Osaka']
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
            'speech': '',
            'displayText': '',
            'source': 'apiai-itinerary',
            'data': data
        }
    elif action in ('Itinerary.location', 'Itinerary.location.Itinerary-location-fallback'):
        data = []
        payload = ['1', '2', '3', '4', '5']
        if userlocale == 'zh_cn':
            speech = '您预计会停留几天？'
            title = ['1', '2', '3', '4', '5']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '您預計會停留幾天？'
            title = ['1', '2', '3', '4', '5']
        else:
            speech = 'For how many days are you planning to stay?'
            title = ['1', '2', '3', '4', '5']
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
    elif action in ('Itinerary.num_days', 'Itinerary.num_days.Itinerary-num_days-fallback'):
        data = []
        payload = ['FIRST', 'SHOPPING', 'KIDS', 'FOOD']
        if userlocale == 'zh_cn':
            speech = '您这次的行程目的是什么呢？'
            title = ['观光 第一次去', '逛街购物', '亲子', '美食']
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '您這次的行程目的是什麼呢？'
            title = ['觀光 第一次去', '逛街購物', '親子', '美食']
        else:
            speech = 'What is your travel theme this time?'
            title = ['First Time', 'Shopping', 'with Kids', 'Food Lover']
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
    elif action in ('Itinerary.theme', 'Itinerary.theme.Itinerary-theme-fallback'):
        city = req['result']['parameters'].get('city')
        num_days = req['result']['parameters'].get('num_days')
        theme = req['result']['parameters'].get('theme')

        if userlocale == 'zh_cn':
            map_title = '地图: %s -> %s'
            button_title = '点击查看'
            speech = '以下是%s天的行程：\n' % num_days
            locale = 'zh_CN'
        elif userlocale in ('zh_tw', 'zh_hk'):
            map_title = '地圖: %s -> %s'
            button_title = '點擊查看'
            speech = '以下是%s天的行程：\n' % num_days
            locale = 'zh_HK'
        else:
            map_title = 'Map: %s -> %s'
            button_title = 'Click to view'
            speech = 'Here is the %s-day itinerary.\n' % num_days
            locale = 'en_US'
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
            for k, day_item in enumerate(d, 1):
                item = day_item.get(locale)

                title = item['name']
                subtitle = item['brief']
                image_url = item['image_url']
                url = item['basic_url']

                fb_item = {
                    'title': 'Day {}-{}: {}'.format(day, k, title),
                    'subtitle': subtitle,
                    'image_url': image_url,
                    'buttons': [
                        {
                            'type': 'web_url',
                            'url': url,
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
                speech += '(%s) %s\n' % (k, title)

            elements += map_data
            data_item = {
                'attachment_type': 'template',
                'attachment_payload': {
                    'template_type': 'generic',
                    'elements': elements
                }
            }
            data.append(data_item)

        datum = make_quick_replies(userlocale)
        data.append(datum)

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
    elif action in ('Transportation', 'Transportation.Transportation-fallback'):
        if userlocale == 'zh_cn':
            speech = '请问需要什么帮忙? (如: 怎么从大阪去东京?)'
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '請問需要什麼幫忙? (如: 怎麼從大阪去東京?)'
        else:
            speech = 'How can I help you? (Ex: How to go to Tokyo from Osaka?)'
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation'
        }
    # elif action == 'Transportation.Transportation-fallback':
    #     if userlocale == 'zh_cn':
    #         speech = '您的目的地是哪里呢? (如: 首尔/银座/江南站等)'
    #     elif userlocale in ('zh_tw', 'zh_hk'):
    #         speech = '您的目的地是哪裡呢? (如: 首爾/銀座/江南站等)'
    #     else:
    #         speech = 'What is your destination? (Ex: Seoul, Ginza, Gangnam station)'
    #     res = {
    #         'speech': speech,
    #         'displayText': speech,
    #         'source': 'apiai-transportation'
    #     }
    elif action in ('Transportation.address-to', 'Transportation.address-to.Transportation-address-to-fallback'):
        if userlocale == 'zh_cn':
            speech = '从哪里出发呢? (如: 首尔/银座/江南站等)'
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '從哪裡出發呢? (如: 首爾/銀座/江南站等)'
        else:
            speech = 'From where? (Ex: Seoul, Ginza, Gangnam station)'
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation'
        }
    elif action in ('Transportation.final', 'Transportation.address-from-to.Transportation-address-from-to-fallback', 'Transportation.address-from.Transportation-address-from-fallback'):
        speech, data = parse_json(req)
        print('Speech:\n%s' % (speech,))
        datum = make_quick_replies(userlocale)
        data.append(datum)
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-transportation',
            'data': data
        }
    elif action in ('Restaurant', 'Restaurant.Restaurant-fallback', 'Restaurant2', 'Restaurant2.Restaurant2-fallback'):
        txt = req['result']['parameters']['txt']
        if txt.startswith('Restaurant') or txt.startswith('餐廳') or txt.startswith('餐厅'):
            if userlocale == 'zh_cn':
                speech = '你想吃那类型及那地区的菜式 (例如: 明洞的韩式餐厅 或者 大阪的寿司)'
            elif userlocale in ('zh_tw', 'zh_hk'):
                speech = '你想吃那類型及那地區的菜式 (例如: 明洞的韓式餐廳 或者 大阪的壽司)'
            else:
                speech = 'How can I help you? (Ex. Can you find me the best Korean food in Seoul, ' \
                         'Please find me a sushi restaurant in Tokyo)'
            res = {
                'speech': speech,
                'displayText': speech,
                'source': 'apiai-restaurant'
            }
        else:
            location = None
            cuisine = None
            parameters = req['originalRequest']['data'].get('parameters')
            if parameters:
                location = parameters.get('location')
                cuisine = parameters.get('cuisine')
            if not location:
                for x in RESTAURANT_LOCATION_KO:
                    if x.lower() in txt.lower():
                        location = x
                        break
                if not location:
                    for x in RESTAURANT_LOCATION_JP:
                        if x.lower() in txt.lower():
                            location = x
                            break
            if not cuisine:
                for x in RESTAURANT_CUISINE_KOREAN:
                    if x.lower() in txt.lower():
                        cuisine = RESTAURANT_CUISINE_KOREAN[0]
                        break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_JAPANESE:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_JAPANESE[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_CHINESE:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_CHINESE[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_WESTERN:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_WESTERN[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_FOREIGN:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_FOREIGN[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_CAFFE:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_CAFFE[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_FASTFOOD:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_FASTFOOD[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_PUB:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_PUB[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_SEAFOOD:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_SEAFOOD[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_ITALIAN:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_ITALIAN[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_FRENCH:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_FRENCH[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_ORGANIC:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_ORGANIC[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_BREAD:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_BREAD[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_YAKINIKU:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_YAKINIKU[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_IZAKAYA:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_IZAKAYA[0]
                            break
                if not cuisine:
                    for x in RESTAURANT_CUISINE_NOODLE:
                        if x.lower() in txt.lower():
                            cuisine = RESTAURANT_CUISINE_NOODLE[0]
                            break

            if location and cuisine:
                geocode_result = gmaps.geocode(location)
                latitude = geocode_result[0]['geometry']['location']['lat']
                longitude = geocode_result[0]['geometry']['location']['lng']
                if location in RESTAURANT_LOCATION_KO:
                    if action in ('Restaurant', 'Restaurant.Restaurant-fallback'):
                        if userlocale == 'zh_cn':
                            lang = '01'
                        elif userlocale in ('zh_tw', 'zh_hk'):
                            lang = '02'
                        else:
                            lang = '04'
                        category1 = '3000'
                        if cuisine == 'Korean':
                            category2 = '3101'
                        elif cuisine == 'Japanese':
                            category2 = '3102'
                        elif cuisine == 'Chinese':
                            category2 = '3103'
                        elif cuisine == 'Western':
                            category2 = '3104'
                        elif cuisine == 'Foreign':
                            category2 = '3105'
                        elif cuisine == 'Caffe':
                            category2 = '3106'
                        elif cuisine == 'Fastfood':
                            category2 = '3107'
                        elif cuisine == 'Pub':
                            category2 = '3108'
                        else:
                            category2 = ''
                        _data = {
                            'lang': lang,
                            'category1': category1,
                            'category2': category2,
                            'latitude': str(latitude),
                            'longitude': str(longitude),
                            'distance': '7000'
                        }
                        _res = exapi_pengtai(_data)
                        elements = list()
                        speech = ''
                        if not _res.get('list'):
                            speech = 'Sorry, we do not have sufficient data at the moment. ' \
                                     'Please try with different parameters.'
                        else:
                            for i, item in enumerate(_res['list']):
                                fb_item = {
                                    'title': item['name'],
                                    'subtitle': '%s\n%s' % (item['summary'], item['address']),
                                    'image_url': item['imagePath'],
                                    'buttons': [
                                        {
                                            'type': 'web_url',
                                            'url': item['url']
                                        }
                                    ]
                                }
                                if userlocale == 'zh_cn':
                                    fb_item['buttons'][0]['title'] = '点击查看'
                                    speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                        i + 1, item['name'], item['summary'], item['address'],
                                        item['tel'], item['besinessHours']
                                    )
                                elif userlocale in ('zh_tw', 'zh_hk'):
                                    fb_item['buttons'][0]['title'] = '點擊查看'
                                    speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                        i + 1, item['name'], item['summary'], item['address'],
                                        item['tel'], item['besinessHours']
                                    )
                                else:
                                    fb_item['buttons'][0]['title'] = 'Click to view'
                                    speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                        i + 1, item['name'], item['summary'], item['address'],
                                        item['tel'], item['besinessHours']
                                    )
                                elements.append(fb_item)
                    else:
                        headers = {
                            'Authorization': 'Bearer %s' % (TF_DATA_TOKEN,)
                        }
                        _res = requests.get(TF_DATA_URL % (longitude, latitude), headers=headers).json()
                        elements = list()
                        speech = ''
                        if not _res['results'].get('features'):
                            speech = 'Sorry, we do not have sufficient data at the moment. ' \
                                     'Please try with different parameters.'
                        else:
                            for i, item in enumerate(_res['results']['features']):
                                if userlocale == 'zh_cn':
                                    fb_item = {
                                        'title': item['properties']['meta']['zh_CN']['name'],
                                        'subtitle': '%s\n%s' % (item['properties']['meta']['zh_CN']['brief'],
                                                                item['properties']['meta']['zh_CN']['address']),
                                        'image_url': item['properties']['meta']['zh_CN']['image_url'],
                                        'buttons': [
                                            {
                                                'type': 'web_url',
                                                'url': item['properties']['meta']['zh_CN']['basic_url'],
                                                'title': '点击查看'
                                            }
                                        ]
                                    }
                                    speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                        i + 1, item['properties']['meta']['zh_CN']['name'],
                                        item['properties']['meta']['zh_CN']['brief'],
                                        item['properties']['meta']['zh_CN']['address'],
                                        item['properties']['meta']['zh_CN']['contact_number'],
                                        item['properties']['meta']['zh_CN']['business_hours']
                                    )
                                elif userlocale in ('zh_tw', 'zh_hk'):
                                    fb_item = {
                                        'title': item['properties']['meta']['zh_HK']['name'],
                                        'subtitle': '%s\n%s' % (item['properties']['meta']['zh_HK']['brief'],
                                                                item['properties']['meta']['zh_HK']['address']),
                                        'image_url': item['properties']['meta']['zh_HK']['image_url'],
                                        'buttons': [
                                            {
                                                'type': 'web_url',
                                                'url': item['properties']['meta']['zh_HK']['basic_url'],
                                                'title': '點擊查看'
                                            }
                                        ]
                                    }
                                    speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                        i + 1, item['properties']['meta']['zh_HK']['name'],
                                        item['properties']['meta']['zh_HK']['brief'],
                                        item['properties']['meta']['zh_HK']['address'],
                                        item['properties']['meta']['zh_HK']['contact_number'],
                                        item['properties']['meta']['zh_HK']['business_hours']
                                    )
                                else:
                                    fb_item = {
                                        'title': item['properties']['meta']['en_US']['name'],
                                        'subtitle': '%s\n%s' % (item['properties']['meta']['en_US']['brief'],
                                                                item['properties']['meta']['en_US']['address']),
                                        'image_url': item['properties']['meta']['en_US']['image_url'],
                                        'buttons': [
                                            {
                                                'type': 'web_url',
                                                'url': item['properties']['meta']['en_US']['basic_url'],
                                                'title': 'Click to view'
                                            }
                                        ]
                                    }
                                    speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                        i + 1, item['properties']['meta']['en_US']['name'],
                                        item['properties']['meta']['en_US']['brief'],
                                        item['properties']['meta']['en_US']['address'],
                                        item['properties']['meta']['en_US']['contact_number'],
                                        item['properties']['meta']['en_US']['business_hours']
                                    )
                                elements.append(fb_item)
                else:
                    category_l = exapi_gurunavi_category_l(cuisine.lower())
                    _data = {
                        'keyid': GURUNAVI_KEY,
                        'lang': 'en' if userlocale == 'en_us' else userlocale,
                        'category_l': category_l,
                        'latitude': str(latitude),
                        'longitude': str(longitude),
                        'input_coordinates_mode': '2',
                        'range': '500',
                        'format': 'json'
                    }
                    _res = exapi_gurunavi(_data)
                    elements = list()
                    speech = ''
                    if not _res.get('rest'):
                        speech = 'Sorry, we do not have sufficient data at the moment. ' \
                                 'Please try with different parameters.'
                    else:
                        print(_res['rest'])
                        if isinstance(_res['rest'], list):
                            for i, item in enumerate(_res['rest']):
                                fb_item = {
                                    'title': item['name']['name'],
                                    'subtitle': '%s\n%s' % (item['access'], item['contacts']['address']),
                                    'image_url': item['image_url']['thumbnail'],
                                    'buttons': [
                                        {
                                            'type': 'web_url',
                                            'url': item['url']
                                        }
                                    ]
                                }
                                if userlocale == 'zh_cn':
                                    fb_item['buttons'][0]['title'] = '点击查看'
                                    speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                        i + 1, item['name']['name'], item['name']['name_sub'],
                                        item['contacts']['address'],
                                        item['contacts']['tel'], item['business_hour']
                                    )
                                elif userlocale in ('zh_tw', 'zh_hk'):
                                    fb_item['buttons'][0]['title'] = '點擊查看'
                                    speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                        i + 1, item['name']['name'], item['name']['name_sub'],
                                        item['contacts']['address'],
                                        item['contacts']['tel'], item['business_hour']
                                    )
                                else:
                                    fb_item['buttons'][0]['title'] = 'Click to view'
                                    speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                        i + 1, item['name']['name'], item['name']['name_sub'],
                                        item['contacts']['address'],
                                        item['contacts']['tel'], item['business_hour']
                                    )
                                elements.append(fb_item)
                        else:
                            item = _res['rest']
                            fb_item = {
                                'title': item['name']['name'],
                                'subtitle': '%s\n%s' % (item['access'], item['contacts']['address']),
                                'image_url': item['image_url']['thumbnail'],
                                'buttons': [
                                    {
                                        'type': 'web_url',
                                        'url': item['url']
                                    }
                                ]
                            }
                            if userlocale == 'zh_cn':
                                fb_item['buttons'][0]['title'] = '点击查看'
                                speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                    1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                                    item['contacts']['tel'], item['business_hour']
                                )
                            elif userlocale in ('zh_tw', 'zh_hk'):
                                fb_item['buttons'][0]['title'] = '點擊查看'
                                speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                    1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                                    item['contacts']['tel'], item['business_hour']
                                )
                            else:
                                fb_item['buttons'][0]['title'] = 'Click to view'
                                speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                    1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                                    item['contacts']['tel'], item['business_hour']
                                )
                            elements.append(fb_item)

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
                datum = make_quick_replies(userlocale)
                data.append(datum)
                res = {
                    'speech': speech,
                    'displayText': speech,
                    'source': 'apiai-restaurant',
                    'data': data
                }
            else:
                error_count = req['originalRequest']['data'].get('error_count')
                if error_count and error_count >= 2:
                    return
                data = [{
                    'parameters': {
                    },
                    'error': False
                }]
                if location:
                    data[0]['error'] = True
                    data[0]['parameters']['location'] = location
                    if userlocale == 'zh_cn':
                        speech = '有特定想找的餐点吗? (如: 韩式料理/日式料理/寿司/拉面等)'
                    elif userlocale in ('zh_tw', 'zh_hk'):
                        speech = '有特定想找的餐點嗎? (如: 韓式料理/日式料理/壽司/拉麵等)'
                    else:
                        speech = 'Any particular food you are looking for? (Ex. Korean, Japanese, Sushi, Ramen)'
                elif cuisine:
                    data[0]['error'] = True
                    data[0]['parameters']['cuisine'] = cuisine
                    if userlocale == 'zh_cn':
                        speech = '您想找哪个地区的呢? (如: 江南/新宿)'
                    elif userlocale in ('zh_tw', 'zh_hk'):
                        speech = '您想找哪個地區的呢? (如: 江南/新宿)'
                    else:
                        speech = 'Which area do you want to search for? (Ex. Gangnam, Shinjuku)'
                else:
                    data[0]['error'] = True
                    if userlocale == 'zh_cn':
                        speech = '你想吃那类型及那地区的菜式 (例如: 明洞的韩式餐厅 或者 大阪的寿司)'
                    elif userlocale in ('zh_tw', 'zh_hk'):
                        speech = '你想吃那類型及那地區的菜式 (例如: 明洞的韓式餐廳 或者 大阪的壽司)'
                    else:
                        speech = 'How can I help you? (Ex. Can you find me the best Korean food in Seoul, ' \
                                 'Please find me a sushi restaurant in Tokyo)'
                res = {
                    'speech': speech,
                    'displayText': speech,
                    'source': 'apiai-restaurant',
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
        print('url = {}'.format(url))
        _res = urlopen(url).read()
        tmpl = get_response_template(userlocale)
        language = convert_langauge_to_user_locale(language.lower(), userlocale)
        speech = tmpl % (phrase, language, _res.decode())
        print('Speech:\n%s' % (speech,))
        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-translate'
        }
    elif action == 'gurunavi':
        parameters = req['result']['parameters']
        location = parameters.get('address')
        cuisine = parameters.get('gurunavi_cuisine_temp')
        _res = exapi_gurunavi_ex(location, cuisine, userlocale)
        elements = list()
        speech = ''
        if not _res['rest']:
            print('Empty!')
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
                        }
                    ]
                }
                elements.append(fb_item)
                if userlocale == 'zh_cn':
                    fb_item['buttons'][0]['title'] = '点击查看'
                    speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                        i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                        item['contacts']['tel'], item['business_hour']
                    )
                elif userlocale in ('zh_tw', 'zh_hk'):
                    fb_item['buttons'][0]['title'] = '點擊查看'
                    speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                        i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                        item['contacts']['tel'], item['business_hour']
                    )
                else:
                    fb_item['buttons'][0]['title'] = 'Click to view'
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
        if req['result']['parameters'].get('country'):
            if req['result']['parameters'].get('country').lower() == 'korea':
                country = 'korea'
            else:
                country = 'japan'
        else:
            country = 'unknown'

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

            if country == 'japan':
                category_l = exapi_gurunavi_category_l(cuisine)
                print('category_l is {}'.format(category_l))
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
                category2 = ''
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

        elements = list()
        speech = ''
        if action == 'restaurant':
            if country == 'japan':
                if lang == '01':
                    lang = 'zh_cn'
                elif lang == '02':
                    lang = 'zh_tw'
                else:
                    lang = 'en'
                _data = {
                    'keyid': GURUNAVI_KEY,
                    'lang': lang,
                    'category_l': category_l,
                    'latitude': str(latitude),
                    'longitude': str(longitude),
                    'input_coordinates_mode': '2',
                    'range': '500',
                    'format': 'json'
                }
                _res = exapi_gurunavi(_data)
                if not _res.get('rest'):
                    if userlocale == 'en_us':
                        speech = 'Sorry, we do not have sufficient data at the moment. ' \
                                 'Please try with different parameters.'
                    elif userlocale in ('zh_hk', 'zh_tw'):
                        speech = 'Sorry, we do not have sufficient data at the moment. ' \
                                 'Please try with different parameters.'  # Todo: translation
                    else:
                        speech = 'Sorry, we do not have sufficient data at the moment. ' \
                                 'Please try with different parameters.'  # Todo: translation
                else:
                    for i, item in enumerate(_res['rest']):
                        fb_item = {
                            'title': item['name']['name'],
                            'subtitle': '%s\n%s' % (item['access'], item['contacts']['address']),
                            'image_url': item['image_url']['thumbnail'],
                            'buttons': [
                                {
                                    'type': 'web_url',
                                    'url': item['url']
                                }
                            ]
                        }
                        elements.append(fb_item)
                        if userlocale == 'zh_cn':
                            fb_item['buttons'][0]['title'] = '点击查看'
                            speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                                item['contacts']['tel'], item['business_hour']
                            )
                        elif userlocale in ('zh_tw', 'zh_hk'):
                            fb_item['buttons'][0]['title'] = '點擊查看'
                            speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                                item['contacts']['tel'], item['business_hour']
                            )
                        else:
                            fb_item['buttons'][0]['title'] = 'Click to view'
                            speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                i + 1, item['name']['name'], item['name']['name_sub'], item['contacts']['address'],
                                item['contacts']['tel'], item['business_hour']
                            )
            elif country == 'korea':
                _data = {
                    'lang': lang,
                    'category1': category1,
                    'category2': category2,
                    'latitude': str(latitude),
                    'longitude': str(longitude),
                    'distance': '10000'
                }
                _res = exapi_pengtai(_data)
                if not _res['list']:
                    print('Empty')
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
                        if userlocale == 'zh_cn':
                            speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                i + 1, item['name'], item['summary'], item['address'],
                                item['tel'], item['besinessHours']
                            )
                        elif userlocale in ('zh_tw', 'zh_hk'):
                            speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                i + 1, item['name'], item['summary'], item['address'],
                                item['tel'], item['besinessHours']
                            )
                        else:
                            speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                i + 1, item['name'], item['summary'], item['address'],
                                item['tel'], item['besinessHours']
                            )
            else:
                _data = {
                    'lang': lang,
                    'category1': category1,
                    'category2': category2,
                    'latitude': str(latitude),
                    'longitude': str(longitude),
                    'distance': '10000'
                }
                _res = exapi_pengtai(_data)
                if not _res:
                    print('NOT FOUND IN PENGTAI, NOW GO TO GURUNAVI')
                    _data = {
                        'key_id': GURUNAVI_KEY,
                        'lang': lang,
                        'category_l': category_l,
                        'latitude': str(latitude),
                        'longitude': str(longitude),
                        'input_coordinates_mode': '2',
                        'range': '500',
                        'format': 'json'
                    }
                    _res = exapi_gurunavi(_data)
                    if not _res['rest']:
                        print('Empty!')
                    else:
                        for i, item in enumerate(_res['rest']):
                            fb_item = {
                                'title': item['name']['name'],
                                'subtitle': '%s\n%s' % (item['access'], item['contacts']['address']),
                                'image_url': item['image_url']['thumbnail'],
                                'buttons': [
                                    {
                                        'type': 'web_url',
                                        'url': item['url'],
                                        'title': button_title
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
                else:
                    if not _res['list']:
                        print('Empty!')
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
                            if userlocale == 'zh_cn':
                                speech += '%s. 名称: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                    i + 1, item['name'], item['summary'], item['address'],
                                    item['tel'], item['besinessHours']
                                )
                            elif userlocale in ('zh_tw', 'zh_hk'):
                                speech += '%s. 名稱: %s\n簡介: %s\n地址: %s\n連絡電話: %s\n營業時間: %s\n\n' % (
                                    i + 1, item['name'], item['summary'], item['address'],
                                    item['tel'], item['besinessHours']
                                )
                            else:
                                speech += '%s. Name: %s\nSummary: %s\nAddress: %s\nTel: %s\nBusiness hours: %s\n\n' % (
                                    i + 1, item['name'], item['summary'], item['address'],
                                    item['tel'], item['besinessHours']
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

        datum = make_quick_replies(userlocale)
        data.append(datum)

        res = {
            'speech': speech,
            'displayText': speech,
            'source': 'apiai-restaurant',
            'data': data
        }
    elif action == 'restaurant.init':
        if userlocale == 'zh_cn':
            speech = '首尔哪里有不错的韩式料理？'
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '首爾哪裡有不錯的韓式料理？'
        else:
            speech = 'How can I help?'
        res = {
            'speech': speech,
            'displayText': '',
            'source': 'apiai-restaurant',
            'data': ''
        }
    elif action in ('restaurant.country-cuisine', 'restaurant.country-cuisine.Restaurant-countrycuisine-fallback'):
        if userlocale == 'zh_cn':
            speech = '您想找哪个地区的呢? (如: 江南/新宿)'
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '首爾哪裡有不錯的韓式料理? (如: 江南/新宿)'
        else:
            speech = 'Which area do you want to search for? (ex. Gangnam, Shinjuku)'
        res = {
            'speech': speech,
            'displayText': '',
            'source': 'apiai-restaurant',
            'data': ''
        }
    elif action in ('restaurant.location', 'restaurant.country', 'Restaurant.location.Restaurant-location-fallback', 'restaurant.country.Restaurant-country-fallback'):
        if userlocale == 'zh_cn':
            speech = '有特定想找的餐点吗? (如: 韩式料理/日式料理/寿司/拉面等)'
        elif userlocale in ('zh_tw', 'zh_hk'):
            speech = '有特定想找的餐點嗎? (如: 韓式料理/日式料理/壽司/拉麵等)'
        else:
            speech = 'Any particular food that you are looking for? (Ex. Korean, Japanese, Sushi, Ramen)'
        res = {
            'speech': speech,
            'displayText': '',
            'source': 'apiai-restaurant',
            'data': ''
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


@app.route('/weather', methods=['GET'])
def weather():
    city = request.args.get('city')
    date = request.args.get('date')
    if not date:
        date = ''
    isForecast = request.args.get('forecast')
    language = request.args.get('language')

    request_data = {
        'city': city,
        'date': date,
        'isForecast': isForecast,
        'language': language
    }

    speech = weather_speech(request_data)
    if speech is None:
        return None

    res = {
        'speech': speech,
        'data': ''
    }

    res = json.dumps(res, indent=4)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'

    return r


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    print('Starting app on port %d' % port)
    app.run(debug=False, port=port, host='0.0.0.0')
