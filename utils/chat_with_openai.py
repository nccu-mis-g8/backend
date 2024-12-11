import openai
from dotenv import load_dotenv
import os

load_dotenv(override=True)
openai.api_key = os.getenv("OPENAI_API_KEY")


def get_response_from_openai(chat_template):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o", messages=chat_template, temperature=1.0
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"發生錯誤: {str(e)}")
        return None
