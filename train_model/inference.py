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


def inference(model_dir: str, input_text: str, user_id: str) -> List[str] | None:
    print("== model dir:" + model_dir)
    try:
        device_map = "auto" if torch.cuda.is_available() else "cpu"
        model = AutoModelForCausalLM.from_pretrained(
            model_dir,
            device_map=device_map,
        )
        print("checkpoint 0")
        model = PeftModel.from_pretrained(model, model_dir)
        print("checkpoint 1")
        tokenizer = AutoTokenizer.from_pretrained(model_dir)

        user_history = TrainingFileRepo.find_trainingfile_by_user_id(user_id=user_id)

        chat = [{"role": "system", "content": "你是我的朋友，請你以和過去回答相同的語氣與我聊天，注意回答的內容要符合問題。"}]

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

        prompt = tokenizer.apply_chat_template(
            chat, tokenize=False, add_generation_prompt=True
        )
        inputs = tokenizer(
            prompt, return_tensors="pt", padding=True, truncation=True, max_length=256
        )
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)

        generate_two_responses = random.random() < 0.5
        num_return_sequences = 2 if generate_two_responses else 1

        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            do_sample=True,
            max_length=128,
            top_k=30,
            top_p=0.85,
            temperature=0.6,
            num_return_sequences=num_return_sequences,
        )

        generated_texts = [
            tokenizer.decode(output, skip_special_tokens=True) for output in outputs
        ]

        return generated_texts
    except Exception as e:
        print(f"Error in inference:{e}")
        return None
