import telebot
import time
import re
import json
import requests
from telebot import types
from functools import lru_cache
from telebot import apihelper
from bs4 import BeautifulSoup as BS

#
url = 'http://www.cbr.ru/'

# config.json contain token, login, password ipv4, etc.,
# to connect to proxy server and bot, using unique bot token
with open('config.json', 'r') as config:
    data = json.load(config)

# Due to telegram is blocked in Russian Federation, use proxy to override the block
apihelper.proxy = {'https': f'socks5://{data["data"]["login"]}:{data["data"]["password"]}.'
                            f'{data["data"]["ipv4"]}:{data["data"]["port"]}'}
bot = telebot.TeleBot(f'{data["data"]["token"]}')


def gen(lst_iterable):
    for date in lst_iterable:
        yield date


# parse data from CB RF site
# url = 'http://www.cbr.ru/'
@lru_cache(maxsize=32)
def parser(url_search, req_unit, req_date):
    source = requests.get(url_search).text
    soup = BS(source, 'lxml')
    body = soup.body.find('div', class_="widgets-draggable ui-sortable").table.tbody
    time_upd = soup.body.find('div', class_="widgets-draggable ui-sortable").table. \
        tbody.th.next_siblings
    # Time part
    upd_weak = None  # 11.02.2020
    upd_new = None  # 12.02.2020
    for time_cur in gen(time_upd):
        if time_cur == '\n':
            pass
        else:
            if upd_weak is not None:
                upd_new = time_cur.string
            else:
                upd_weak = time_cur.string
    # Currency part
    usd_eur_weak = body.find_all('td', class_="weak")
    match = re.compile(r'\d{2}.+\d{2,6}')
    usd_weak = match.findall(usd_eur_weak[0].text.strip())[0]  # 63,7708
    eur_weak = match.findall(usd_eur_weak[1].text.strip())[0]  # 69,8226

    courses = body.find_all('div', class_="w_data_wrap")
    usd_upd = None
    eur_upd = None
    for j, i in enumerate(courses):
        if j == 0:
            usd_upd = match.findall(i.text)[0]
        elif j == 1:
            eur_upd = match.findall(i.text)[0]

    dict_currencies = {}
    # Merge together time and currencies' courses
    dict_currencies['usd'] = {'info':
                                  {'date':
                                       {'prev':
                                            (upd_weak, usd_weak), 'new': (upd_new, usd_upd)}}}
    dict_currencies['eur'] = {'info':
                                  {'date':
                                       {'prev':
                                            (upd_weak, eur_weak), 'new': (upd_new, eur_upd)}}}

    if req_unit == 'eur':
        if req_date == 'new':
            return json.dumps(dict_currencies['eur']['info']['date']['new'], indent=2)
        elif req_date == 'old':
            return json.dumps(dict_currencies['eur']['info']['date']['prev'], indent=2)
    elif req_unit == 'usd':
        if req_date == 'new':
            return json.dumps(dict_currencies['usd']['info']['date']['new'], indent=2)
        elif req_date == 'old':
            return json.dumps(dict_currencies['usd']['info']['date']['prev'], indent=2)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 """What does this bot do?\n
It makes your your work as a lawyer easier While drawing up statements of claim,
\nyou may easily get access to currency exchange rate to calculate the amount of claim.
To get started type: /commands""")


@bot.message_handler(commands=['commands'])
def about(message):
    # bot.reply_to(message, 'CB exchange rate type: /menu ')
    bot.send_message(message.chat.id, "Type /menu")


@bot.message_handler(commands=['menu'])
def currencies(message):
    markup_menu = types.ReplyKeyboardMarkup(row_width=2)
    itembtn1 = types.KeyboardButton('/usd_new')
    itembtn2 = types.KeyboardButton('/usd_old')
    itembtn3 = types.KeyboardButton('/eur_new')
    itembtn4 = types.KeyboardButton('/eur_old')

    markup_menu.add(itembtn1, itembtn2, itembtn3, itembtn4)
    bot.send_message(message.chat.id, "Choose one option from the menu", reply_markup=markup_menu)


@bot.message_handler(commands=['usd_new'])
def usd_new(msg):
    bot.reply_to(msg, parser(url, 'usd', 'new'))


@bot.message_handler(commands=['usd_old'])
def usd_old(msg):
    bot.reply_to(msg, parser(url, 'usd', 'old'))


@bot.message_handler(commands=['eur_new'])
def usd_old(msg):
    bot.reply_to(msg, parser(url, 'eur', 'new'))


@bot.message_handler(commands=['eur_old'])
def usd_old(msg):
    bot.reply_to(msg, parser(url, 'eur', 'old'))


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=5)
        except:
            time.sleep(10)
