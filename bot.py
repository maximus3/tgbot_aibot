import telebot
import json
import logging
import cherrypy
import apiai

from config import *
from webhook import *

logging.basicConfig(format = u'%(filename)s[LINE:%(lineno)d]# %(levelname)-8s [%(asctime)s]  %(message)s', level = logging.INFO, filename = directory + 'aibot.log')

# WEBHOOK_START

# Наш вебхук-сервер
class WebhookServer(object):
    @cherrypy.expose
    def index(self):
        if 'content-length' in cherrypy.request.headers and \
                        'content-type' in cherrypy.request.headers and \
                        cherrypy.request.headers['content-type'] == 'application/json':
            length = int(cherrypy.request.headers['content-length'])
            json_string = cherrypy.request.body.read(length).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            # Эта функция обеспечивает проверку входящего сообщения
            bot.process_new_updates([update])
            return ''
        else:
            raise cherrypy.HTTPError(403)

# WEBHOOK_FINISH

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands = ['start'])
def start(message):
    mid = message.chat.id

    href = 'https://dialogs.yandex.ru/store/skills/0168730f-moya-buhgalteri/'
    word = message.text.split()
    word.pop(0)
    if word == []:
        word = 'Текст'
    else:
        if 'http' in word[-1]:
            href = word.pop()
        word = ' '.join(word)

    text = 'Привет'

    if message.chat.first_name:
        text = text + ' <' + message.chat.first_name + '>'
    if message.chat.last_name:
        text = text + ' <' + message.chat.last_name + '>'
    if message.chat.username:
        text = text + ' <' + message.chat.username + '>'

    bot.send_message(mid, text + '''
*%s*
_%s_
`%s`
[%s](%s)
'''%(word, word, word, word, href), parse_mode = 'Markdown', disable_web_page_preview = True)

@bot.message_handler(content_types = ['text'])
def main(message):
    text = message.text
    mid = message.chat.id

    if '*' in text or '_' in text or '`' in text or '[' in text or '(' in text:
        bot.send_message(mid, text, parse_mode = 'Markdown', disable_web_page_preview = True)
        return

    if mid not in admin_ids:
        return

    logging.info('Connecting to DF')
    request = apiai.ApiAI(TOKEN_AI).text_request() # Токен API к Dialogflow
    logging.info('Connected')
    request.lang = 'ru' # На каком языке будет послан запрос
    request.session_id = str(mid) # ID Сессии диалога (нужно, чтобы потом учить бота)
    logging.info('Sending text to DF')
    request.query = text # Посылаем запрос к ИИ с сообщением от юзера
    logging.info('Sent')
    logging.info('Getting result from DF')
    responseJson = json.loads(request.getresponse().read().decode('utf-8'))
    logging.info('Got')
    response = responseJson['result']['fulfillment']['speech'] # Разбираем JSON и вытаскиваем ответ
    bot.send_message(mid, str(responseJson))
    action = ''
    parameters = {}
    contexts = []
    if 'action' in responseJson['result']:
        action = responseJson['result']['action']
    if 'parameters' in responseJson['result']:
        parameters = responseJson['result']['parameters']
    if 'contexts' in responseJson['result']:
        contexts = responseJson['result']['contexts']
    if action:
        bot.send_message(mid, "Action: " + action)
    if parameters:
        bot.send_message(mid, "Parameters: " + str(parameters))
    if contexts:
        bot.send_message(mid, "Contexts: " + str(contexts))
        
    # Если есть ответ от бота - присылаем юзеру, если нет - бот его не понял
    if response:
        logging.info('Have answer')
        bot.send_message(mid, response)
    else:
        logging.info('No answer')
        bot.send_message(mid, 'Я Вас не совсем понял!')

# WEBHOOK_START

# Снимаем вебхук перед повторной установкой (избавляет от некоторых проблем)
bot.remove_webhook()

# Ставим заново вебхук
bot.set_webhook(url=WEBHOOK_URL_BASE + WEBHOOK_URL_PATH,
                certificate=open(WEBHOOK_SSL_CERT, 'r'))

# Указываем настройки сервера CherryPy
cherrypy.config.update({
    'server.socket_host': WEBHOOK_LISTEN,
    'server.socket_port': WEBHOOK_PORT,
    'server.ssl_module': 'builtin',
    'server.ssl_certificate': WEBHOOK_SSL_CERT,
    'server.ssl_private_key': WEBHOOK_SSL_PRIV
})

 # Собственно, запуск!
cherrypy.quickstart(WebhookServer(), WEBHOOK_URL_PATH, {'/': {}})

# WEBHOOK_FINISH
