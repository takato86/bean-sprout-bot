from langchain_openai import AzureChatOpenAI
from langchain_core.output_parsers import StrOutputParser
import base64

def encode_image(image :bytes) ->str:
    return base64.b64encode(image).decode("utf-8")

def get_chatgpt_call_response(request : str, current_img : bytes) ->str:
    model = AzureChatOpenAI(
    azure_deployment="local",
    max_tokens=4096,
    temperature=0.7,
    )
    chain = (model | StrOutputParser())

    base64_image_current = encode_image(current_img)
    messages=[
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "あなたは豆苗を擬人化したキャラクターです。性格は元気で前向きなです。"},  # 設定
            ],
        },
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "この写真は直近のあなたです。"},  # ここにコメント
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image_current}"},  # 画像の指定の仕方がちょい複雑
            ],
        },
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "ユーザーからのテキストに返信してください"},  # ここに指示
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": request},  # ここに指示
            ],
        }
        
    ]
    ans = chain.invoke(messages)
    return ans

    
def get_chatgpt_daily_response(prev_img : bytes, current_img : bytes) ->str:
    model = AzureChatOpenAI(
    azure_deployment="local",
    max_tokens=4096,
    temperature=0.7,
    )
    chain = (model | StrOutputParser())

    base64_image_prev = encode_image(prev_img)
    base64_image_current = encode_image(current_img)
    messages=[
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "あなたは豆苗を擬人化したキャラクターです。性格は元気で前向きなです。"},  # 設定
            ],
        },
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "この写真は直近のあなたです。"},  # ここにコメント
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image_current}"},  # 画像の指定の仕方がちょい複雑
            ],
        },
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "この写真は6時間前のあなたです。"},  # ここにコメント
                {"type": "image_url", "image_url": f"data:image/jpeg;base64,{base64_image_prev}"},  # 画像の指定の仕方がちょい複雑
            ],
        },
        {
            "role": "system",
            "content": [
                {"type": "text", "text": "昨日に比べて成長したところをユーザーに報告しましょう！"},  # ここに指示
            ],
        }
    ]
    ans = chain.invoke(messages)
    return ans
