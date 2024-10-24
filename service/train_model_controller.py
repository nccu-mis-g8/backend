from flask import Blueprint, request, Response, jsonify
from flasgger import swag_from
import logging
import json
from flask_jwt_extended import get_jwt_identity, jwt_required
import torch
import random

import traceback
import time

from sqlalchemy.sql.functions import user
from models.user import User
from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from service.utils_controller import FILE_DIRECTORY
from train_model.finetune import BASE_MODEL_DIR, train
from train_model.inference import inference
from concurrent.futures import TimeoutError
from requests.exceptions import RequestException
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
import os


train_model_bp = Blueprint("finetune", __name__)
logger = logging.getLogger(__name__)


@train_model_bp.post("/train_model")
@jwt_required()
@swag_from(
    {
        "tags": ["Train"],
        "description": """
    此API用來啟動微調，會回傳開始訓練或是失敗。

    Input:
    - 可以接受與微調相關的任何參數，若未填寫則使用 default 參數。
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回開始訓練。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "model_id",
                "in": "formData",
                "required": True,
                "description": "The model ID used for training",
                "schema": {"type": "integer", "example": 123},
            },
        ],
        "responses": {
            200: {
                "description": "Training started successfully",
                "examples": {
                    "application/json": {
                        "status": "Training started successfully",
                    }
                },
            },
            400: {
                "description": "Bad request, no file to train",
                "examples": {"application/json": {"status": "no file to train"}},
            },
            403: {
                "description": "Forbidden, user info not provided",
                "examples": {"application/json": {"error": "Forbidden"}},
            },
            404: {
                "description": "User or model not found",
                "examples": {"application/json": {"message": "使用者或模型不存在"}},
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
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    
    model_id = request.form.get("model_id")
    if not model_id:
        return jsonify({"error": "model_id is required"}), 400

    try:
        trained_model = TrainedModelRepo.find_trainedmodel_by_user_and_model_id(
            user_id=user.id, model_id=model_id
        )
        if trained_model is None:
            return jsonify({"error": "Model not found"}), 404

        training_file = TrainingFileRepo.find_first_training_file_by_user_and_model_id(
            user_id=user.id, model_id=model_id
        )

        if training_file is None:
            return jsonify({"status": "no file to train"}), 400

        file_path = os.path.join(FILE_DIRECTORY, training_file.filename)

        if not os.path.exists(file_path):
            return jsonify({"status": "no file to train"}), 400

        saved_models = TrainedModelRepo.find_all_trainedmodel_by_user_id(user_id=user.id)
        
        training_file.start_train = True
        TrainingFileRepo.save_training_file()


        TrainedModelRepo.start_trainedmodel(user_id=user.id, model_id=model_id)

    
        model_path = os.path.join("..\\saved_models", trained_model.modelname)
        print(model_path)
        # 如果是第一次训练
        if len(saved_models) == 0 or trained_model.id == model_id:
            print("第一次訓練")
            train(
                str(trained_model.id),
                BASE_MODEL_DIR,
                model_path,
                os.path.join(FILE_DIRECTORY, file_path),
            )
        else:
            last_model = saved_models[-1]
            print(f"接續舊的model: {last_model.id} 繼續訓練")
            # 已經練過了，接續之前練過的model再訓練
            train(
                str(trained_model.id),
                os.path.join("..\\saved_models", last_model.modelname),
                model_path,
                os.path.join(FILE_DIRECTORY, file_path),
            )

        training_file.is_trained = True
        TrainingFileRepo.save_training_file()

        return (
            jsonify(
                {"status": "Training started successfully", "model_id": trained_model.id}
            ),
            200,
        )

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500

@train_model_bp.post("/chat")
@jwt_required()
@swag_from(
    {
        "tags": ["Chat"],
        "description": """
        這個 API 用來與已訓練模型進行聊天。它接收使用者的輸入文本並返回模型的生成回應。

        Input:
        - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
        - user_info: 包含使用者的基本訊息 (例如 user_Id)。
        - input_text: 使用者的聊天輸入。

        Returns:
        - JSON 回應訊息：
          - 成功時：返回生成的聊天回應。
          - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
        """,
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "user_info",
                "in": "formData",
                "type": "string",
                "description": "使用者的訊息，包括 user_Id",
                "required": True,
            },
            {
                "name": "input_text",
                "in": "formData",
                "type": "string",
                "description": "使用者的聊天輸入文本",
                "required": True,
            },
        ],
        "responses": {
            200: {
                "description": "回應成功",
                "examples": {
                    "application/json": {
                        "res": "這是模型生成的回應",
                    }
                },
            },
            400: {
                "description": "輸入錯誤",
                "examples": {"application/json": {"error": "Input text is required"}},
            },
            404: {
                "description": "模型未找到",
                "examples": {
                    "application/json": {"error": "Model directory not found"}
                },
            },
            500: {
                "description": "內部錯誤",
                "examples": {"application/json": {"error": "Internal server error"}},
            },
        },
    }
)
def chat():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_id = request.form.get("user_id")
    if user_id:
        user_id = json.loads(user_id)
    else:
        return jsonify({"error": "Forbidden"}), 403

    model_id = request.form.get("model_id")
    if not model_id:
        return jsonify({"error": "model_id is required"}), 400

    trained_model = TrainedModelRepo.find_trainedmodel_by_user_and_model_id(
        user_id=user_id, model_id=model_id
    )

    if trained_model is None:
        return jsonify({"error": "Model not found"}), 404
    # print(user_id)
    model_dir = os.path.abspath(
        os.path.join("..", "saved_models", trained_model.modelname)
    )

    if not os.path.exists(model_dir):
        return jsonify({"error": "Model directory not found"}), 404

    input_text = request.form.get("input_text", "")

    if not input_text:
        return jsonify({"error": "Input text is required"}), 400

    try:
        responses = inference(model_dir, input_text, user.id)

        if responses is None:
            return jsonify({"error": "Inference failed"}), 500

        response_data = {
            "result": [
                {"input": input_text, "output": response} for response in responses
            ],
            "msg": f"成功取得{len(responses)}筆回答",
        }
        return (
            Response(
                json.dumps(response_data, ensure_ascii=False),
                content_type="application/json; charset=utf-8",
            ),
            200,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500