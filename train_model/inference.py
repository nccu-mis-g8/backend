import os
import random
import torch
import time
import pandas as pd
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from repository.trainingfile_repo import TrainingFileRepo
from typing import List

model_cache = {}
model_usage_counter = {}
usage_threshold = 5 
total_memory = torch.cuda.get_device_properties(0).total_memory
threshold = int(total_memory * 0.8)

def manage_model_cache():
    global model_cache, model_usage_counter

    current_memory = torch.cuda.memory_allocated()
    if current_memory < threshold:
        return

    least_used_models = sorted(model_usage_counter.items(), key=lambda x: x[1])

    for user_id, _ in least_used_models:
        if user_id in model_cache:
            if model_usage_counter[user_id] < usage_threshold: 
                del model_cache[user_id]
                del model_usage_counter[user_id]
                torch.cuda.empty_cache()
                print(f"Removed model for user_id: {user_id}")
            current_memory = torch.cuda.memory_allocated()
            if current_memory < threshold:
                break


def load_model_for_user(model_dir: str, user_id: str):
    global model_cache, model_usage_counter
    if user_id in model_cache:
        print(f"Using cached model for user_id: {user_id}")
        model_usage_counter[user_id] += 1

        # 检查是否超出使用次数
        if model_usage_counter[user_id] >= usage_threshold:
            manage_model_cache()
            # 如果当前模型被清理，则重新加载
            if user_id not in model_cache:
                print(f"Reloading model for user_id: {user_id} after cache cleanup")
                return load_model_for_user(model_dir, user_id)
            else:
                model_usage_counter[user_id] = 0  # 重置计数器

        return model_cache[user_id]

    print(f"Loading model for user_id: {user_id}")
    # adapter_config_path = os.path.join(model_dir, "adapter_config.json")
    # if os.path.exists(adapter_config_path):
    #     print(f"PEFT adapter configuration found at {adapter_config_path}. Loading PEFT model...") 
    # else:
    #     model = PeftModel.from_pretrained(model, model_dir)
    #     print("No adapter_config.json found. Loading base model without PEFT.")
    model = AutoModelForCausalLM.from_pretrained(model_dir)
    if not hasattr(model, "peft_config"):
        model = PeftModel.from_pretrained(model, model_dir)
    model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model_cache[user_id] = (model, tokenizer)
    model_usage_counter[user_id] = 1

    return model, tokenizer

def limit_stickers(text: str) -> str:
    #限制貼圖、貼文、照片的數量
    max_stickers = 2
    max_posts = 2
    max_photos = 2

    sticker_tokens = text.split("[貼圖]")
    if len(sticker_tokens) > max_stickers:
        text = "[貼圖]".join(sticker_tokens[:max_stickers]) + sticker_tokens[max_stickers]

    post_tokens = text.split("[貼文]")
    if len(post_tokens) > max_posts:
        text = "[貼文]".join(post_tokens[:max_posts]) + post_tokens[max_posts]

    photo_tokens = text.split("[照片]")
    if len(photo_tokens) > max_photos:
        text = "[照片]".join(photo_tokens[:max_photos]) + photo_tokens[max_photos]

    return text


def inference(model_dir: str, input_text: str, user_id: str) -> List[str] | None:
    try:
        greetings = ["晚上好","明天見","安安","午安","晚安","早安","早阿","早", "你好", "哈囉", "嗨","掰掰","拜拜","掰","拜","掰囉","拜囉","掰掰囉","拜拜囉","再見", "hello", "hi", "hey", "good morning", "good afternoon", "good evening"]

        # 如果輸入屬於招呼語，返回相同的招呼語
        if input_text.lower().strip() in [greet.lower() for greet in greetings]:
            delay_seconds = random.uniform(3, 7)
            time.sleep(delay_seconds)
            return [input_text]
        
        model, tokenizer = load_model_for_user(model_dir, user_id)

        chat = []
        user_history = TrainingFileRepo.find_trainingfile_by_user_id(user_id=user_id)
        if isinstance(user_history, list) and user_history:
            training_file = random.choice(user_history)
        else:
            training_file = user_history

        if training_file and os.path.exists(training_file.filename):
            with open(training_file.filename, 'r') as f:
                df = pd.read_csv(f)
            num_samples = 5
            if len(df) > num_samples:
                df_sample = df.tail(n=num_samples)
            else:
                df_sample = df

            for _, row in df_sample.iterrows():
                chat.append(f"User: {row['input']}")
                chat.append(f"Assistant: {row['output']}")

        # 先前對話
        # sys_context = "這是之前的對話紀錄，請根據對話紀錄進行回覆"
        # user_context = "要不要一起吃飯？"
        # assistant_context = "吃甚麼？"
        # chat.append(f"System: {sys_context}")
        # chat.append(f"User: {user_context}")
        # chat.append(f"Assistant: {assistant_context}")

        chat.append(f"User: {input_text}")
        chat.append("Assistant:")

        prompt = "\n".join(chat)

        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=256 
        ).to(model.device)

        generate_two_responses = random.random() < 0.5
        num_return_sequences = 2 if generate_two_responses else 1

        outputs = model.generate(
            input_ids=inputs["input_ids"],
            attention_mask=inputs["attention_mask"],
            do_sample=True,
            max_length=128,
            top_k=30,
            top_p=0.85,
            temperature=0.7,
            num_return_sequences=num_return_sequences
        )

        responses = []
        for i, output in enumerate(outputs):
            generated_text = tokenizer.decode(output, skip_special_tokens=True).strip()
            generated_text = limit_stickers(generated_text)

            if "Assistant:" in generated_text:
                generated_text = generated_text.split("Assistant:")[-1].strip()

            tags_to_remove = ["ANCES","ANS","ANSE","ANSION","ANTS","[檔案]","<<SYS>>","INSTP", "[/INST]", "INST","[You]","[User]", "User", "[Assistant]", "Assistant", "\\n:", ":", "[你]", "[我]", "[輸入]", "ERM [/D]", "ANCE ", "S]", "\\", "/"]
            for tag in tags_to_remove:
                generated_text = generated_text.replace(tag, "").strip()

            if input_text in generated_text:
                generated_text = generated_text.replace(input_text, "").strip()

            generated_text = " ".join(line for line in generated_text.splitlines() if line.strip())

            responses.append(generated_text)

        return responses

    except Exception as e:
        print(f"Error in inference: {e}")
        return None
