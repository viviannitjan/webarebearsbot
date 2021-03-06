# -*- coding: utf-8 -*-

#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

import os
import sys
import urllib.parse
import requests
import psycopg2
from argparse import ArgumentParser

from flask import Flask, request, abort
from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

app = Flask(__name__)

# get channel_secret and channel_access_token from your environment variable
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
db_url = os.getenv('DATABASE_URL', None)

if channel_secret is None: 
    print('Specify LINE_CH name in postgresql as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

line_bot_api = LineBotApi(channel_access_token)
handler = WebhookHandler(channel_secret)

def calculate(expr):
    expr=urllib.parse.quote(expr)
    link = "http://api.mathjs.org/v4/?expr=" + expr
    response = requests.get(link)
    return response

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    sys.stdout.flush()
    app.logger.info("Request body: " + body)
    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def message_text(event):
    if (event.message.text=="/history"):
        uid = str(event.source.user_id)
        conn = psycopg2.connect(db_url, sslmode='require') 
        cur = conn.cursor() 
        cur.execute("select * from calc_history where uid = '%s';" % (uid))
        results = cur.fetchall()
        content =""
        if (len(results)>0):
            for i in range (0,len(results)):
                content += results[i][0] + results[i][1] + "\n"
        else : 
            content = "No calculation before"
        conn.commit() 
        conn.close()
    else:
        content = calculate(event.message.text).text
        uid = str(event.source.user_id)
        conn = psycopg2.connect(db_url, sslmode='require') 
        cur = conn.cursor() 
        cur.execute("insert into calc_history (uid,expression,result) values ('%s','%s','%s');" %(uid,event.message.text,content))
        conn.commit() 
        conn.close()
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=content)
    )


if __name__ == "__main__":
    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', default=8000, help='port')
    arg_parser.add_argument('-d', '--debug', default=False, help='debug')
    options = arg_parser.parse_args()

    app.run(debug=options.debug, port=options.port)