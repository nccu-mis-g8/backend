import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def analyze_and_modify_response(response: str, history: list) -> str:

    prompt = (
        f"請你分析以下的對話，學習 output 歷史對話者的語氣並判斷 output是否合理，"
        f"請注意合理的話請不要做改動，不合理請協助改正或新增內容。"
        f"不合理的情況除了情境之外，也不能透漏自己是 AI人工智慧，因為聊天回覆者是用戶的好朋友才對。"
        f"另外，請將 [貼圖] 替換成對話情境合適的表情符號，再將結果直接放到output即可，不須用說明改動原因。\n"
        f"歷史對話：{history}\n"
        f"Output: {response}"
    )

    try:
        openai_response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "你是一個分析對話語氣的專家。"},
                {"role": "user", "content": prompt},
            ],
        )
        return openai_response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"Error in OpenAI API: {e}")
        return response