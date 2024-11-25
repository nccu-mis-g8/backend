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
max_cache_size = 3
usage_threshold = 5

total_memory = torch.cuda.get_device_properties(0).total_memory
threshold = int(total_memory * 0.75)


def manage_model_cache():
    global model_cache, model_usage_counter

    current_memory = torch.cuda.memory_allocated()
    print(f"[INFO] Current memory allocated: {current_memory / 1e9:.2f} GB (Threshold: {threshold / 1e9:.2f} GB)")
    
    if current_memory >= threshold or len(model_cache) > max_cache_size:
        print("[INFO] Memory or cache size exceeded. Cleaning up cache...")
        least_used_models = sorted(model_usage_counter.items(), key=lambda x: x[1])
        for user_id, _ in least_used_models:
            if user_id in model_cache:
                print(f"[INFO] Removing model for user_id: {user_id}")
                del model_cache[user_id]
                del model_usage_counter[user_id]
                torch.cuda.empty_cache()

                current_memory = torch.cuda.memory_allocated()
                if current_memory < threshold and len(model_cache) <= max_cache_size:
                    break


def load_model_for_user(model_dir: str, user_id: str):

    global model_cache, model_usage_counter


    if user_id in model_cache:
        print(f"[INFO] Using cached model for user_id: {user_id}")
        model_usage_counter[user_id] += 1
        manage_model_cache()
        return model_cache[user_id]

    print(f"[INFO] Loading model for user_id: {user_id}")
    model = AutoModelForCausalLM.from_pretrained(model_dir)
    if not hasattr(model, "peft_config"):
        model = PeftModel.from_pretrained(model, model_dir)
    model.to(torch.device("cuda" if torch.cuda.is_available() else "cpu"))
    model.eval()

    tokenizer = AutoTokenizer.from_pretrained(model_dir)

    model_cache[user_id] = (model, tokenizer)
    model_usage_counter[user_id] = 1

    manage_model_cache()

    return model, tokenizer

def limit_stickers(text: str) -> str:
    # 限制貼圖、貼文、照片的數量
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


def inference(model_dir: str, input_text: str, user_id: str, max_retries:int = 3) -> List[str] | None:
    try:
        greetings = [
            "晚上好",
            "明天見",
            "安安",
            "午安",
            "晚安",
            "早安",
            "早阿",
            "早",
            "你好",
            "哈囉",
            "嗨",
            "掰掰",
            "拜拜",
            "掰",
            "拜",
            "掰囉",
            "拜囉",
            "掰掰囉",
            "拜拜囉",
            "再見",
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
        ]

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
            with open(training_file.filename, "r") as f:
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
            prompt, return_tensors="pt", padding=True, truncation=True, max_length=256
        ).to(model.device)


        for attempt in range(max_retries):
            try:
                generate_two_responses = random.random() < 0.5
                num_return_sequences = 2 if generate_two_responses else 1

                with torch.no_grad():
                    outputs = model.generate(
                        input_ids=inputs["input_ids"],
                        attention_mask=inputs["attention_mask"],
                        do_sample=True,
                        max_length=128,
                        top_k=30,
                        top_p=0.85,
                        temperature=0.7,
                        num_return_sequences=num_return_sequences,
                    )

                responses = []
                for i, output in enumerate(outputs):
                    generated_text = tokenizer.decode(output, skip_special_tokens=True).strip()
                    generated_text = limit_stickers(generated_text)

                    if "Assistant:" in generated_text:
                        generated_text = generated_text.split("Assistant:")[-1].strip()

                    tags_to_remove = [
                        "ANTER",
                        "問：",
                        "問題：",
                        "入題",
                        "回答：",
                        "答：",
                        "問題：",
                        "入題",
                        "回答：",
                        "[入戲]",
                        "ANCES",
                        "ANS",
                        "ANSE",
                        "ANSION",
                        "ANTS",
                        "[檔案]",
                        "<<SYS>>",
                        "INSTP",
                        "[/INST]",
                        "INST",
                        "[You]",
                        "[User]",
                        "User",
                        "[Assistant]",
                        "Assistant",
                        "\\n:",
                        ":",
                        "[你]",
                        "[我]",
                        "[輸入]",
                        "ERM [/D]",
                        "ANCE ",
                        "S]",
                        "\\",
                        "/",
                        "(null)",
                        "null"
                    ]
                    for tag in tags_to_remove:
                        generated_text = generated_text.replace(tag, "").strip()

                    if input_text in generated_text:
                        generated_text = generated_text.replace(input_text, "").strip()

                    generated_text = " ".join(
                        line for line in generated_text.splitlines() if line.strip()
                    )

                    responses.append(generated_text)

                    if any(responses):
                        return responses
                    
                    print(f"[WARN] Attempt {attempt + 1}: Empty response. Retrying...")
                    time.sleep(1)
                
            except torch.cuda.OutOfMemoryError:
                    print(f"[ERROR] CUDA Out of Memory during attempt {attempt + 1}. Cleaning up...")
                    torch.cuda.empty_cache()
                    time.sleep(5) 
            except Exception as e:
                if "524" in str(e):
                    print(f"[WARN] 524 Timeout encountered on attempt {attempt + 1}. Retrying...")
                else:
                    print(f"[ERROR] Inference attempt {attempt + 1} failed: {e}")

            print("[ERROR] All inference attempts failed or returned empty responses.")
            return None


    except Exception as e:
        print(f"Error in inference: {e}")
        return None
