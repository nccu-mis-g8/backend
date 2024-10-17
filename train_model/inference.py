import os
import json
import random
import torch
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from flask import jsonify, Response
import traceback
from requests.exceptions import RequestException
from concurrent.futures import TimeoutError
from repository.trainingfile_repo import TrainingFileRepo
from typing import List
import re

def inference(model_dir: str, input_text: str, user_id: str) -> List[str] | None:
    try:
        model = AutoModelForCausalLM.from_pretrained(model_dir)
        if not hasattr(model, "peft_config"):
            model = PeftModel.from_pretrained(model, model_dir)
        tokenizer = AutoTokenizer.from_pretrained(model_dir)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)

        chat = []

        # 從資料庫中找到用戶的歷史資料
        user_history = TrainingFileRepo.find_trainingfile_by_user_id(user_id=user_id)

        if isinstance(user_history, list) and user_history:
            training_file = random.choice(user_history) 
        else:
            training_file = user_history

        if training_file is None:
            return None

        file_path = training_file.filename

        if os.path.exists(file_path):
            df = pd.read_csv(file_path)

            num_samples = 5
            if len(df) > num_samples:
                df_sample = df.tail(n=num_samples)
            else:
                df_sample = df

            for _, row in df_sample.iterrows():
                chat.append({"role": "user", "content": row["input"]})
                chat.append({"role": "assistant", "content": row["output"]})

        chat.append({"role": "user", "content": f"{input_text}"})

        # 直接構建對話，而不使用 apply_chat_template
        prompt = " ".join([message["content"] for message in chat])

        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=256).to(device)
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)

        # 生成回應
        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            do_sample=True,
            max_length=128,
            top_k=30,
            top_p=0.85,
            temperature=0.6,
            num_return_sequences=1  # 確保生成一個簡單回應
        )

        generated_texts = [tokenizer.decode(output, skip_special_tokens=True).strip() for output in outputs]

        # 使用正則表達式過濾掉多餘的模板部分
        cleaned_texts = []
        for text in generated_texts:
            # 移除「### 指令」及相關模板信息
            cleaned_text = re.sub(r"### 指令.*### 回覆：", "", text)
            cleaned_texts.append(cleaned_text.strip())

        return cleaned_texts
    except Exception as e:
        print(f"Error in inference: {e}")
        return None