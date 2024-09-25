from flask import Blueprint, request, Response, jsonify
from flasgger import swag_from
import logging
import json

import traceback
import time

from sqlalchemy.sql.functions import user
from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from service.utils_controller import FILE_DIRECTORY
from train_model.finetune import BASE_MODEL_DIR, train
from concurrent.futures import TimeoutError
from requests.exceptions import RequestException
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
            user_id=user
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
     此 API 用於啟動聊天服務。


    Returns:
    - JSON 回應訊息：
      - 成功時：返回訊息。
      - 失敗時：返回錯誤訊息，可能是server錯誤或server反應間間過長。
    """,
        "parameters": [
            {
                "name": "input_text",
                "in": "body",
                "type": "string",
                "required": True,
                "description": "Input text for the chat",
            }
        ],
        "responses": {
            200: {
                "description": "Generated chat response",
                "examples": {"application/json": {"response": "Generated text"}},
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
def chat():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")
    trained_model = TrainedModelRepo.find_trainedmodel_by_user_id(user_id=user_id)
    model_dir = BASE_MODEL_DIR
    if trained_model is not None:
        model_dir = str(os.path.join("..\\saved_models", trained_model.modelname))
    try:
        input_text = request.json.get("input_text", "")
        if not input_text:
            return jsonify({"error": "Input text is required"}), 400
        instruction = "你是我的朋友，請你以和過去回答相同的語氣與我聊天，注意回答的內容要符合問題。"
        full_input = [
            {"role": "system", "content": instruction},
            {"role": "user", "content": input_text},
        ]

        start_time = time.time()
        sequences = generator(
            full_input,
            do_sample=True,
            top_p=0.9,
            temperature=0.7,
            num_return_sequences=1,
            eos_token_id=tokenizer.eos_token_id,
            # max_new_tokens=50,
            max_length=70,
            # truncation=True,
        )

        # 之後會改小
        if time.time() - start_time > 3000:
            return jsonify({"error": "Request timeout, please try again"}), 504

        generated_text = ""
        for message in sequences[0]["generated_text"]:
            if message["role"] == "assistant":
                generated_text = message["content"]
                break

        response = json.dumps({"response": generated_text}, ensure_ascii=False)
        return Response(response, content_type="application/json; charset=utf-8")

    except (RequestException, TimeoutError) as e:
        return jsonify({"error": "Error in generating response, please try again"}), 500

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500
