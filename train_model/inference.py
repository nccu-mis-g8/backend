import os
import random
import torch
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from repository.trainingfile_repo import TrainingFileRepo
from typing import List

# 模型緩存字典
model_cache = {}

def load_model_for_user(model_dir: str, user_id: str):
    """為特定用戶加載模型並緩存"""
    if user_id in model_cache:
        print(f"Using cached model for user_id: {user_id}")
        return model_cache[user_id]

    print(f"Loading model for user_id: {user_id}")
    model = AutoModelForCausalLM.from_pretrained(model_dir)
    if not hasattr(model, "peft_config"):
        model = PeftModel.from_pretrained(model, model_dir)
    model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model_cache[user_id] = (model, tokenizer)
    return model, tokenizer

def inference(model_dir: str, input_text: str, user_id: str) -> List[str] | None:
    try:
        # 加載模型和 Tokenizer
        model, tokenizer = load_model_for_user(model_dir, user_id)

        # 獲取用戶歷史記錄
        chat = []
        user_history = TrainingFileRepo.find_trainingfile_by_user_id(user_id=user_id)
        if isinstance(user_history, list) and user_history:
            training_file = random.choice(user_history)
        else:
            training_file = user_history

        if training_file and os.path.exists(training_file.filename):
            df = pd.read_csv(training_file.filename)
            num_samples = 3
            if len(df) > num_samples:
                df_sample = df.tail(n=num_samples)
            else:
                df_sample = df

            for _, row in df_sample.iterrows():
                chat.append(f"User: {row['input']}")
                chat.append(f"Assistant: {row['output']}")

        chat.append(f"User: {input_text}")
        chat.append("Assistant:")

        prompt = "\n".join(chat)

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256  # 增加一些上下文長度限制
        ).to(model.device)

        # 生成回應
        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            do_sample=True,
            max_length=128,
            top_k=30,
            top_p=0.85,
            temperature=0.7,
            num_return_sequences=1
        )

        generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

        tags_to_remove = ["INSTP", "[/INST]", "INST","[User]","User","[Assistant]","Assistant"]
        for tag in tags_to_remove:
            generated_text = generated_text.replace(tag, "").strip()

        if "Assistant:" in generated_text:
            generated_text = generated_text.split("Assistant:")[-1].strip()

        return [generated_text]

    except Exception as e:
        print(f"Error in inference: {e}")
        return None

