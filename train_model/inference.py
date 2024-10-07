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

def generate_response(model_dir, input_text,user_id):
    try:
        if not os.path.exists(model_dir):
            return jsonify({"error": "Model directory not found"}), 404

        model = AutoModelForCausalLM.from_pretrained(model_dir)
        model = PeftModel.from_pretrained(model, model_dir)
        tokenizer = AutoTokenizer.from_pretrained(model_dir)

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model.to(device)

        user_history = TrainingFileRepo.find_trainingfile_by_user_id(user_id=user_id)

        chat = [
            {"role": "system", "content": "你是我的朋友，請你以和過去回答相同的語氣與我聊天，注意回答的內容要符合問題。"}
        ]

        if isinstance(user_history, list) and user_history:
            training_file = random.choice(user_history) 
        else:
            training_file = user_history

        file_path = training_file.filename

        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            
            num_samples = 5
            if len(df) > num_samples:
                df_sample = df.sample(n=num_samples)
            else:
                df_sample = df

            for _, row in df_sample.iterrows():
                chat.append({"role": "user", "content": row["input"]})
                chat.append({"role": "assistant", "content": row["output"]})

        chat.append({"role": "user", "content": f"{input_text}"})

        prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=256)
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
            num_return_sequences=num_return_sequences
        )

        generated_texts = [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]

        result_data = []
        for generated_text in generated_texts:
            result_data.append({
                "input": input_text,
                "output": generated_text.strip()
            })

        response_data = {
            "result": result_data,
            "msg": f"成功取得{len(result_data)}筆回答"
        }

        response = json.dumps(response_data, ensure_ascii=False)
        return Response(response, content_type="application/json; charset=utf-8")

    except (RequestException, TimeoutError) as e:
        return jsonify({"error": "Error in generating response, please try again"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500