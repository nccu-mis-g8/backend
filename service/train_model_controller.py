from typing import Optional
from flask import Blueprint, current_app, request, Response, jsonify
from flasgger import swag_from
import logging
import json
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.wrappers import response


from models.trained_model import TrainedModel
from models.training_file import TrainingFile
from models.user import User
from repository.shared_model_repo import SharedModelRepo
from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from service.utils_controller import FILE_DIRECTORY
from train_model.finetune import BASE_MODEL_DIR, train
from train_model.inference import inference
import os
import threading


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

        saved_models = TrainedModelRepo.find_all_trainedmodel_by_user_id(
            user_id=user.id
        )

        training_file.start_train = True
        TrainingFileRepo.save_training_file()

        TrainedModelRepo.start_trainedmodel(user_id=user.id, model_id=model_id)

        model_path = os.path.join("..\\saved_models", trained_model.modelname)
        print(model_path)
        app = current_app.app_context()
        # 如果是第一次训练
        if len(saved_models) == 0 or str(trained_model.id) == model_id:
            print("第一次訓練")
            threading.Thread(
                target=start_train,
                args=(
                    app,
                    str(trained_model.id),
                    training_file.id,
                    BASE_MODEL_DIR,
                    model_path,
                    os.path.join(FILE_DIRECTORY, file_path),
                ),
            ).start()
        else:
            last_model = saved_models[-1]
            print(f"接續舊的model: {last_model.id} 繼續訓練")
            # 已經練過了，接續之前練過的model再訓練
            threading.Thread(
                target=start_train,
                args=(
                    app,
                    str(trained_model.id),
                    training_file.id,
                    os.path.join("..\\saved_models", last_model.modelname),
                    model_path,
                    os.path.join(FILE_DIRECTORY, file_path),
                ),
            ).start()

        return (
            jsonify(
                {
                    "status": "Training started successfully",
                    "model_id": trained_model.id,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)}), 500


def start_train(
    app, id: str, training_file_id: int, model_dir: str, save_dir: str, data_path: str
):
    with app.app_context():
        train(id, training_file_id, model_dir, save_dir, data_path)


@train_model_bp.post("/chat")
@jwt_required()
@swag_from(
    {
        "tags": ["Chat"],
        "description": """
        這個 API 用來與已訓練模型進行聊天。它接收使用者的輸入文本並返回模型的生成回應。

        Input:
        - Authorization header 必須包含 Bearer token 以進行身份驗證。
        - user_info: 包含使用者的基本訊息 (例如 user_Id)。
        - input_text: 使用者的聊天輸入。
        - session_history: JSON 格式的對話歷史，包含最近幾次的用戶輸入與模型回應。

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
                "name": "is_shared",
                "in": "formData",
                "type": "string",
                "description": "是不是分享來的 model",
                "required": True,
            },
            {
                "name": "modelname",
                "in": "formData",
                "type": "string",
                "description": "選擇要聊天的 modelname（注意：不是 model_id，是 modelname）",
                "required": True,
            },
            {
                "name": "input_text",
                "in": "formData",
                "type": "string",
                "description": "使用者的聊天輸入文本",
                "required": True,
            },
            {
                "name": "session_history",
                "in": "formData",
                "type": "string",
                "description": """JSON 格式的對話歷史，包含最近幾次的用戶輸入與模型回應。
                例如：[{"user": "哈囉", "model": "哈囉"},{"user": "你起床了嗎", "model": "剛起來怎麼嘞"}]
                """,
                "required": False,
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

    user_id = user.id

    is_shared = request.form.get("is_shared")
    modelname = request.form.get("modelname")
    if not modelname:
        return jsonify({"error": "modelname is required"}), 400
    # 取得模型
    trained_model: Optional[TrainedModel] = None
    if is_shared == "false":
        trained_model = TrainedModelRepo.find_trainedmodel_by_user_and_modelname(
            user_id=user_id, modelname=modelname
        )
    else:
        trained_model = SharedModelRepo.find_trainedmodel_by_modelname_and_acquirer_id(
            modelname=modelname, acquirer_id=user_id
        )

    if trained_model is None:
        return jsonify({"error": "未找到模型，請確認有模型訪問權限"}), 404

    model_dir = os.path.abspath(
        os.path.join("..", "saved_models", trained_model.modelname)
    )

    if not os.path.exists(model_dir):
        return jsonify({"error": "Model directory not found"}), 404

    input_text = request.form.get("input_text", "")

    if not input_text:
        return jsonify({"error": "Input text is required"}), 400

    # session_history
    history_json = request.form.get("session_history", "[]")
    try:
        session_history = json.loads(history_json)
        if not isinstance(session_history, list):
            return (
                jsonify({"error": "Invalid session_history format. Must be a list."}),
                400,
            )
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid session_history JSON"}), 400

    try:
        responses = inference(model_dir, input_text, user.id, session_history)

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


@train_model_bp.post("/share-model")
@jwt_required()
@swag_from(
    {
        "tags": ["Model Sharing"],
        "description": "Share a trained model.",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "required": True,
                "description": "Bearer token for authorization",
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "modelname",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "The name of the trained model to be shared",
            },
        ],
        "responses": {
            "200": {
                "description": "Model successfully shared",
                "examples": {
                    "application/json": {
                        "msg": "成功建立模型分享",
                        "modelname": "example_model_name",
                        "link": "uuid",
                    }
                },
            },
            "404": {
                "description": "User or model not found",
                "examples": {"application/json": {"message": "使用者不存在"}},
            },
            "403": {
                "description": "Forbidden - Model does not belong to the user",
                "examples": {"application/json": {"message": "無法取用該模型"}},
            },
            "500": {
                "description": "Failed to create shared model",
                "examples": {"application/json": {"message": "無法建立模型分享"}},
            },
        },
    }
)
def share_model():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    # parameter
    modelname = request.form.get("modelname")
    #
    model = TrainedModelRepo.find_trainedmodel_by_user_and_modelname(
        user_id=user.id, modelname=modelname
    )
    if model is None:
        return jsonify(message="無法找到模型"), 404
    if model.user_id != user.id:
        return jsonify(message="無法取用該模型"), 403
    shared_model = SharedModelRepo.create_shared_model(model)
    if shared_model is None:
        return jsonify(message="無法建立模型分享"), 500
    return (
        jsonify(
            {"msg": "成功建立模型分享", "modelname": model.modelname, "link": shared_model.link}
        ),
        200,
    )


@train_model_bp.route("/model/<string:link>", methods=["GET"])
@jwt_required()
@swag_from(
    {
        "tags": ["Model Sharing"],
        "description": "Retrieve access to a shared model.",
        "parameters": [
            {
                "name": "Authorization",
                "in": "header",
                "type": "string",
                "required": True,
                "schema": {"type": "string", "example": "Bearer "},
            },
            {
                "name": "link",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "Unique link identifier for the shared model",
            },
        ],
        "responses": {
            "200": {
                "description": "Successfully retrieved model access",
                "examples": {"application/json": {"message": "成功取得模型權限"}},
            },
            "404": {
                "description": "User or shared model not found, or user does not have access",
                "examples": {"application/json": {"message": "使用者不存在"}},
            },
        },
    }
)
def get_shared_model(link: str):
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    res = SharedModelRepo.obtain_shared_model(link, user.id)
    # 成功
    if res["res"]:
        return jsonify(message=res["msg"]), 200
    # 失敗
    return jsonify(message=res["msg"]), 404
