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
from train_model.inference import inference
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
@swag_from(
    {
        "tags": ["Chat"],
        "description": """
        這個 API 用來與已訓練模型進行聊天。它接收使用者的輸入文本並返回模型的生成回應。

        Input:
        - user_info: 包含使用者的基本訊息 (例如 user_Id)。
        - input_text: 使用者的聊天輸入。

        Returns:
        - JSON 回應訊息：
          - 成功時：返回生成的聊天回應。
          - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
        """,
        "parameters": [
            {
                "name": "user_info",
                "in": "formData",
                "type": "string",
                "description": "使用者的訊息，包括 user_Id",
                "required": True
            },
            {
                "name": "input_text",
                "in": "formData",
                "type": "string",
                "description": "使用者的聊天輸入文本",
                "required": True
            }
        ],
        "responses": {
            200: {
                "description": "回應成功",
                "examples": {
                    "application/json": {
                        "res": "這是模型生成的回應",
                    }
                }
            },
            400: {
                "description": "輸入錯誤",
                "examples": {
                    "application/json": {"error": "Input text is required"}
                },
            },
            404: {
                "description": "模型未找到",
                "examples": {
                    "application/json": {"error": "Model directory not found"}
                }
            },
            500: {
                "description": "內部錯誤",
                "examples": {
                    "application/json": {"error": "Internal server error"}
                }
            }
        },
    }
)
def chat():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")
    trained_model = TrainedModelRepo.find_trainedmodel_by_user_id(user_id=user_id)

    if trained_model is None:
        return jsonify({"error":"Model not found"}),404
    
    model_dir = os.path.abspath(os.path.join("..", "saved_models", trained_model.modelname))

    if not os.path.exists(model_dir):
        return jsonify({"error": "Model directory not found"}), 404
        
    input_text = request.form.get("input_text", "")

    if not input_text:
        return jsonify({"error": "Input text is required"}), 400

    try:
        responses = inference(model_dir, input_text, user_id)
        
        if responses is None:
            return jsonify({"error": "Inference failed"}), 500
        
        response_data = {
            "result": [{"input": input_text, "output": response} for response in responses],
            "msg": f"成功取得{len(responses)}筆回答"
        }
        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500