from flask import Blueprint, request, Response, jsonify
from flasgger import swag_from
import logging
import json
import torch
import random

import traceback
import time

from sqlalchemy.sql.functions import user
from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from service.utils_controller import FILE_DIRECTORY
from train_model.finetune import BASE_MODEL_DIR, train
from concurrent.futures import TimeoutError
from requests.exceptions import RequestException
from transformers import AutoTokenizer,AutoModelForCausalLM
from peft import PeftModel
import os


train_model_bp = Blueprint("finetune", __name__)
logger = logging.getLogger(__name__)


@train_model_bp.post("/train_model")
@swag_from(
    {
        "tags": ["Train"],
        "description": """
    此API用來啟動微調，會回傳開始訓練或是失敗。

    Input:
    - 可以接受與微調相關的任何參數，若未填寫則使用 default 參數。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回開始訓練。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "responses": {
            200: {
                "description": "Training started successfully",
                "examples": {
                    "application/json": {
                        "status": "Training started successfully",
                    }
                },
            },
            500: {
                "description": "Internal server error",
                "examples": {
                    "application/json": {"status": "Error", "message": "Error message"}
                },
            },
        },
    }
)
def train_model():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")
    try:
        # 取得user要train的file
        training_file = TrainingFileRepo.find_first_training_file_by_user_id(
            user_id=user_id
        )
        if training_file is None:
            return (
                jsonify({"status": "no file to train"}),
                400,
            )
        file_path = os.path.join(FILE_DIRECTORY, training_file.filename)

        if not os.path.exists(file_path):
            return (
                jsonify({"status": "no file to train"}),
                400,
            )

        saved_models = TrainedModelRepo.find_all_trainedmodel_by_user_id(user_id)
        new_model = TrainedModelRepo.create_trainedmodel(user_id)
        if new_model is None:
            return jsonify({"status": "Error", "message": "Internel Error"}), 500
        training_file.start_train = True
        TrainingFileRepo.save_training_file()
        # 如果是第一次
        if len(saved_models) == 0:
            print("第一次訓練")
            train(
                str(new_model.id),
                BASE_MODEL_DIR,
                str(os.path.join("..\\saved_models", new_model.modelname)),
                os.path.join(FILE_DIRECTORY, file_path),
            )
        else:
            last_model = saved_models[-1]
            print(f"接續舊的model: {last_model.id} 繼續訓練")
            # 已經練過了，接續之前練過的model再訓練
            train(
                str(new_model.id),
                str(os.path.join("..\\saved_models", last_model.modelname)),
                str(os.path.join("..\\saved_models", new_model.modelname)),
                os.path.join(FILE_DIRECTORY, file_path),
            )

        # 把拿去train的資料is_trained設成true
        training_file.is_trained = True
        TrainingFileRepo.save_training_file()
        return (
            jsonify(
                {"status": f"Training started successfully. Model id: {new_model.id}"}
            ),
            200,
        )
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@train_model_bp.post("/chat")
@train_model_bp.post("/chat")
def chat():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")
    trained_model = TrainedModelRepo.find_trainedmodel_by_user_id(user_id=user_id)

    if trained_model is not None:
        model_dir = os.path.abspath(os.path.join("..", "saved_models", trained_model.modelname))

        if not os.path.exists(model_dir):
            return jsonify({"error": "Model directory not found"}), 404

        # 加載模型和 tokenizer
        model = AutoModelForCausalLM.from_pretrained(model_dir)
        model = PeftModel.from_pretrained(model, model_dir)
        tokenizer = AutoTokenizer.from_pretrained(model_dir)
    
    try:
        input_text = request.form.get("input_text", "")
        if not input_text:
            return jsonify({"error": "Input text is required"}), 400

        # 設置設備
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # 確保模型移動到正確的設備
        model.to(device)

        chat = [
            {"role": "system", "content": "你是我的朋友，請你以和過去回答相同的語氣與我聊天，注意回答的內容要符合問題。"},
            {"role": "user", "content": f"{input_text}"},
        ]

        prompt = tokenizer.apply_chat_template(chat, tokenize=False, add_generation_prompt=True)

        inputs = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=256)
        input_ids = inputs["input_ids"].to(device)
        attention_mask = inputs["attention_mask"].to(device)

        # 決定是否生成兩個回應
        generate_two_responses = random.random() < 0.5
        num_return_sequences = 2 if generate_two_responses else 1

        outputs = model.generate(
            input_ids=input_ids,
            attention_mask=attention_mask,
            do_sample=True,
            max_length=256,
            top_k=50,
            top_p=0.95,
            temperature=0.7,
            num_return_sequences=num_return_sequences
        )

        generated_texts = [tokenizer.decode(output, skip_special_tokens=True) for output in outputs]

        if num_return_sequences == 2:
            response_data = {
                "res1": generated_texts[0],
                "res2": generated_texts[1],
                "mes": "選擇您認為更好的回答"
            }
        else:
            response_data = {"res": generated_texts[0]}

        response = json.dumps(response_data, ensure_ascii=False)
        return Response(response, content_type="application/json; charset=utf-8")

    except (RequestException, TimeoutError) as e:
        return jsonify({"error": "Error in generating response, please try again"}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
