import os
import logging
import boto3
from boto3.dynamodb.conditions import Key, Attr
import datetime
from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    FlexMessage,
    FlexContainer
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    PostbackEvent,
    PostbackContent
)
from linebot.v3.messaging.models.show_loading_animation_request import (
    ShowLoadingAnimationRequest
)

from chatgpt import get_chatgpt_daily_response,get_chatgpt_call_response
from line import post_message_with_image
from weather import get_current_weather

BUCKET_NAME = 'bean-sprouts-growing'

app = Flask(__name__)

app.logger.setLevel(logging.INFO)
configuration = Configuration(access_token=os.getenv("CHANNEL_TOKEN"))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# logging.basicConfig(filename='/var/log/flask.log', level=logging.DEBUG, format=f'%(asctime)s %(levelname)s %('
#                                                                                   f'name)s %(threadName)s : %(message)s')


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@app.route("/health", methods=['GET'])
def health():
    return 'OK'

@app.route("/post", methods=['GET'])
def post():
    print("START")
    app.logger.info("START /post")
    s3 = boto3.resource(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
    )
    bucket = s3.Bucket(BUCKET_NAME)
    img_objs = sorted([obj for obj in bucket.objects.all()], key=lambda x: x.key)
    # rawフォルダの画像は利用しない。
    img_objs = [img_obj for img_obj in img_objs if 'raw' not in img_obj.key]
    prev_img_obj = img_objs[-2]
    prev_img_response = prev_img_obj.get()
    app.logger.info(f"Loaded img from {prev_img_obj.key}")
    current_img_obj = img_objs[-1]
    current_img_response = current_img_obj.get()
    app.logger.info(f"Loaded img from {current_img_obj.key}")
    prev_img, current_img = prev_img_response['Body'].read(), current_img_response['Body'].read()
    
    app.logger.info("Start Weather method")

    try:
        weather = get_current_weather()
        weatherIconUrl = f"https://openweathermap.org/img/wn/{weather['icon']}.png"
    except Exception as e:
        app.logger.exception("OpenWeatherMap returned a error.")
        weatherIconUrl = ''

    app.logger.info("Finish Weather method")
    
    app.logger.info("Start ChatGPT method")
    chatgpt_text = get_chatgpt_daily_response(prev_img, current_img)
    app.logger.info("Finish ChatGPT method")
    
    current_img_url = f"https://{BUCKET_NAME}.s3.ap-northeast-1.amazonaws.com/{current_img_obj.key}"
    app.logger.info("Start LINE method")
    post_message_with_image(chatgpt_text, current_img_url)
    app.logger.info("Finish LINE method")
    
    app.logger.info("Start Registration DynamoDB")
    dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
    
    try:
        table = dynamodb.Table('line-bot-hands-on-table')
        table.put_item(
            Item={
                'publisherId': "o0001",  # ここは配信側のID想定
                'timestamp': int(datetime.datetime.now().timestamp()),
                'generatedMessage': chatgpt_text,
                'imgUrl': current_img_url,
                'weatherIconUrl': weatherIconUrl
            }
        )
    except Exception as e:
        app.logger.exception("Exception when calling AppRunner->Dynamo DB: %s\n" % e)
        return "NG"

    app.logger.info("Succeeded Putting data to Dynamo DB")
    app.logger.info("FINISH /post")
    return 'OK'


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        s3 = boto3.resource(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        bucket = s3.Bucket(BUCKET_NAME)
        img_objs = sorted([obj for obj in bucket.objects.all()], key=lambda x: x.key)
        current_img_obj = img_objs[-1]
        current_img_response = current_img_obj.get()
        current_img = current_img_response['Body'].read()
        line_bot_api = MessagingApi(api_client)
        
        show_loading_animation_request = ShowLoadingAnimationRequest(chatId=event.source.user_id, loadingSeconds=10)

        try:
            api_response = line_bot_api.show_loading_animation(show_loading_animation_request)
            app.logger.info(api_response)
            app.logger.info(f"Request to ChatGPT, {event.message.text}")
            text = get_chatgpt_call_response(event.message.text, current_img)
            app.logger.info(f"Response from ChatGPT, {text}")
            api_response = line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=text)]
                )
            )
            app.logger.info(api_response)
        except Exception as e:
            app.logger.exception("Exception when calling MessagingApi->mark_messages_as_read: %s\n" % e)


@handler.add(PostbackEvent)
def handle_list_records(event):
    with ApiClient(configuration) as api_client:
        dynamodb = boto3.resource('dynamodb', region_name='ap-northeast-1')
    
        try:
            table = dynamodb.Table('line-bot-hands-on-table')
            response = table.query(KeyConditionExpression=Key('publisherId').eq('o0001'), Limit=5, ScanIndexForward=False)
            app.logger.info(f"response: {response}")
            items = response['Items']
            contents = []
            
            for item in reversed(items):
                
                if item.get("weatherIconUrl") is None:
                    heading = {
                        "type": "text",
                        "text": datetime.date.fromtimestamp(int(item["timestamp"])).isoformat(),
                        "weight": "bold",
                        "size": "md",
                        "wrap": True,
                        "offsetBottom": "sm"
                    }
                    message = {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": item["generatedMessage"],
                                "wrap": True,
                                "color": "#8c8c8c",
                                "size": "xs",
                                "flex": 5
                            }
                        ]
                    }
                else:
                    heading = {
                        "type": "box",
                        "layout": "baseline",
                        "contents": [
                          {
                            "type": "text",
                            "text": datetime.date.fromtimestamp(int(item["timestamp"])).isoformat(),
                            "weight": "bold",
                            "size": "md",
                            "flex": 0
                          },
                          {
                            "type": "icon",
                            "size": "xxl",
                            "scaling": True,
                            "offsetTop": "md",
                            "offsetBottom": "none",
                            "offsetStart": "none",
                            "url": item["weatherIconUrl"]
                          }
                        ],
                        "offsetTop": "-15px"
                    }
                    message = {
                        "type": "box",
                        "layout": "baseline",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "text",
                                "text": item["generatedMessage"],
                                "wrap": True,
                                "color": "#8c8c8c",
                                "size": "xs",
                                "flex": 5
                            }
                        ],
                        "offsetTop": "-11px"
                    }

                content = {
                    "type": "bubble",
                    "size": "kilo",
                    "hero": {
                        "type": "image",
                        "url": item["imgUrl"],
                        "size": "full",
                        "aspectMode": "cover",
                        "aspectRatio": "16:9"
                    },
                    "body": {
                        "type": "box",
                        "layout": "vertical",
                        "contents": [
                            heading,
                            message
                        ]
                    }
                }
                contents.append(content)
            
            carousel = {
                "type": "carousel",
                "contents": contents
            }
            message = FlexMessage(alt_text="bean-sprouts-list", contents=FlexContainer.from_dict(carousel))
            line_bot_api = MessagingApi(api_client)
            line_bot_api.reply_message_with_http_info(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[message]
                )
            )
            app.logger.info("Send Flex Message!")
        except Exception as e:
            app.logger.exception("Exception when reading AppRunner->DynamoDB: %s\n" % e)
            return
            


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=8080)
    app.logger.setLevel(logging.INFO)

