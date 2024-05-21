import os
import json
import requests


def post_message_with_image(message, image):
    data = {
        "messages": [
            {
                "type": "text",
                "text": message
                },
            {
                "type": "image",
                "originalContentUrl": image,
                "previewImageUrl": image
                }
                ],
        "notificationDisabled": True
    }

    json_data = json.dumps(data)

    response = requests.post(
        "https://api.line.me/v2/bot/message/broadcast",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('CHANNEL_TOKEN')}"
            },
        data=json_data,
    )

    print(response.status_code)
    print(response.json())