import openai
import os
import json

openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_and_modify_response(input:str,response: str,history_context:str) -> str:
    prompt = (
        f"以下是用戶的歷史對話記錄，請模仿用戶的說話風格進行回應：\n"
        f"{history_context}\n\n"
        f"請檢查以下對話，檢查是否是符合情境的回答，並根據用戶的語氣進行修正：\n"
        f"1. 如果情境回答合理，保留不變；\n"
        f"2. 如果情境回答不合理，請根據用戶的語氣做修正；\n"
        f"3. 不得包含與語境無關或令人困惑的內容；\n"
        f"4. 若出現 [貼圖] 則替換為合適的表情符號；\n\n"
        f"Input: {input}\n\n"
        f"Output: {response}\n\n"
        f"返回結果應只有修正後的 Output，無其他說明。"
    )

    try:
        final_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "請根據歷史對話記錄學習用戶的說話風格，並用類似的語氣進行回應，避免不合理的回覆，若本來output就沒有[貼圖]則不用自行添加表情符號。"
                        "回答應該自然、親近，像親密好友一樣表現出關心和支持。避免用正式的語氣，使用日常對話中的語言。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
        )

        return final_response["choices"][0]["message"]["content"]

        
    except Exception as e:
        print(f"Error in OpenAI API: {e}")
        return response