from flask import (
    Blueprint,
    request,
    jsonify,
)
from flasgger import swag_from
from flask_jwt_extended import get_jwt_identity, jwt_required
from repository.trainedmodel_repo import TrainedModelRepo
from repository.trainingfile_repo import TrainingFileRepo
from models.user import User
import json
import os
import logging
import utils.linetxt_to_llama as linetxt_to_llama

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


FILE_DIRECTORY = "..\\training_file"


def allowed_file(filename, extension):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == extension


# TODO: remove this api after testing
@utils_bp.get("/")
def hello_world():
    return "Hello, World!"


@utils_bp.post("/user/upload_csv_file")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": """
        此API 用於上傳 CSV 檔案。

        Input:
        - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
        - user_info: 使用者的資訊，必須是 JSON 格式。
        - file: 要上傳的 CSV 檔案。
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
                "required": True,
                "description": "User information in JSON format",
            },
            {
                "name": "file",
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "The CSV file to upload",
            },
        ],
        "responses": {
            "200": {
                "description": "File uploaded successfully",
                "examples": {
                    "application/json": {"message": "File uploaded successfully"}
                },
            },
            "400": {
                "description": "Bad request due to missing file or wrong file type",
                "examples": {
                    "application/json": {"error": "No file part in the request"}
                },
            },
            "403": {
                "description": "Forbidden request",
                "examples": {"application/json": {"error": "Forbidden"}},
            },
            "500": {
                "description": "Internal Error",
                "examples": {"application/json": {"error": "Internal Server Error"}},
            },
        },
    }
)
def upload_csv_file():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")

    # 確認使用者是否存在
    user_exists = User.is_user_id_exists(user_id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 csv
    if file and allowed_file(file.filename, "csv"):
        # 確認目錄是否存在，若不存在則創建目錄

        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = TrainingFileRepo.find_first_training_file_by_user_id(
            user_id=user_id
        )

        is_renew = False  # 是否是覆蓋舊的
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file is not None and (current_file.is_trained is False):
            delete_file_path = os.path.join(FILE_DIRECTORY, current_file.filename)
            os.remove(delete_file_path)
            TrainingFileRepo.delete_training_file_by_file_id(current_file.id)
            is_renew = True
        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(
            user_id=user_id, original_file_name=file.filename
        )
        if saved_file is None:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )
        file.save(os.path.join(FILE_DIRECTORY, saved_file.filename))
        if is_renew:
            return jsonify({"message": "File update successfully"}), 200
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only CSV files are allowed."}),
            400,
        )


@utils_bp.post("/user/training_files")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": """
    此 API 用於拿到指定 user_Id 的訓練檔案。用戶必須通過 Bearer token 進行身份驗證，並且在請求體中提供 `user_Id` 來獲取相應的訓練檔案。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
    - `user_Id` 在請求體中傳遞，指定用戶 ID 來獲取訓練檔案。
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
                "name": "user_Id",
                "in": "formData",
                "type": "string",
                "required": True,
                "description": "User id in JSON format",
                "example": '{"user_Id": "5"}',
            },
        ],
        "responses": {
            "200": {
                "description": "A training file object for the user",
                "schema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "integer", "example": 1},
                        "user_Id": {"type": "integer", "example": 123},
                        "filename": {"type": "string", "example": "file.csv"},
                        "original_file_name": {
                            "type": "string",
                            "example": "my_file.csv",
                        },
                        "is_trained": {"type": "boolean", "example": False},
                        "upload_time": {
                            "type": "string",
                            "example": "2024-09-26 15:30:00",
                        },
                    },
                },
            },
            "400": {
                "description": "Invalid user_Id",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {"type": "string", "example": "Invalid user_Id"},
                    },
                },
            },
            "404": {
                "description": "No training files found for this user",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "No training files found for this user。",
                        },
                    },
                },
            },
            "500": {
                "description": "Server error while fetching training files",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "An error occurred while fetching training files。",
                        },
                    },
                },
            },
        },
    }
)
def get_user_training_files():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_Id = request.form.get("user_Id")

    # 確認使用者是否存在
    user_exists = User.is_user_id_exists(user_Id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404

    try:
        training_file = TrainingFileRepo.find_first_training_file_by_user_id(user_Id)

        if not training_file:
            return jsonify({"message": "No training files found for this user."}), 404

    except Exception as e:
        logging.error(f"Error retrieving training files for user {user}: {e}")
        return (
            jsonify({"message": "An error occurred while fetching training files."}),
            500,
        )

    return (
        jsonify(
            {
                "id": training_file.id,
                "user_id": training_file.user_id,
                "filename": training_file.filename,
                "original_file_name": training_file.original_file_name,
                "is_trained": training_file.is_trained,
                "upload_time": training_file.upload_time.strftime("%Y-%m-%d %H:%M:%S"),
            }
        ),
        200,
    )


@utils_bp.post("/user/upload_txt_file")
@jwt_required()
@swag_from(
    {
        "tags": ["Utils"],
        "description": """
    此 API 用於上傳 txt file，然後轉為 csv file 儲存。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
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
                "description": "JSON string containing user_Id and master_name",
                "required": True,
                "type": "string",
                "example": '{"user_Id": "12345", "master_name": "John"}',
            },
            {
                "name": "file",
                "in": "formData",
                "description": "TXT file to be uploaded",
                "required": True,
                "type": "file",
            },
        ],
        "responses": {
            200: {
                "description": "File uploaded successfully",
                "schema": {
                    "type": "object",
                    "properties": {
                        "message": {
                            "type": "string",
                            "example": "File uploaded successfully",
                        }
                    },
                },
            },
            400: {
                "description": "Bad request",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "user_Id or master_name is missing",
                        }
                    },
                },
            },
            403: {
                "description": "Forbidden: User info is missing",
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string", "example": "Forbidden"}},
                },
            },
            404: {
                "description": "File not found",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "File not found: /path/to/file",
                        }
                    },
                },
            },
            500: {
                "description": "Internal server error",
                "schema": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "example": "File processing error: error message",
                        }
                    },
                },
            },
        },
    }
)
def upload_txt_file():
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404

    user_info = request.form.get("user_info")

    if user_info:
        try:
            user_info = json.loads(user_info)
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid user_info format"}), 400
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId 和 master_name
    user_id = user_info.get("user_Id")
    master_name = user_info.get("master_name")

    if not user_id or not master_name:
        return jsonify({"error": "user_Id or master_name is missing"}), 400

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files.get("file")

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 txt
    if file and allowed_file(file.filename, "txt"):
        # 確認目錄是否存在，若不存在則創建目錄
        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        # 處理 line chat 的文件
        processor = linetxt_to_llama.LineChatProcessor(
            output_name=user_id, master_name=master_name, data_dir=FILE_DIRECTORY
        )
        try:
            csv_file_name = processor.process(file)  # 假設 process 方法需要文件來處理
            print(csv_file_name)
        except Exception as e:
            return jsonify({"error": f"File processing error: {str(e)}"}), 500

        # 確認是否已有未完成的訓練文件，並刪除
        current_file = TrainingFileRepo.find_first_training_file_by_user_id(
            user_id=user_id
        )
        if current_file is not None and not current_file.is_trained:
            try:
                file_path = os.path.join(FILE_DIRECTORY, current_file.filename)

                if os.path.exists(file_path):
                    os.remove(file_path)
                else:
                    return jsonify({"error": f"File not found: {file_path}"}), 404

                TrainingFileRepo.delete_training_file_by_file_id(current_file.id)
            except OSError as e:
                return jsonify({"error": f"Error deleting old file: {str(e)}"}), 500

        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(
            user_id=user_id, original_file_name=file.filename, filename=csv_file_name
        )
        if saved_file is None:
            return jsonify({"error": "Unable to create file."}), 500

        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only TXT files are allowed."}),
            400,
        )



@utils_bp.get("/user/model_status/<int:model_Id>")
@jwt_required()
@swag_from({
    "tags": ["Utils"],
    'description': '取得指定使用者和模型的訓練狀態和相關信息。',
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'required': True,
            'description': 'JWT Token to authorize the request',
            "schema": {"type": "string", "example": "Bearer "},
        },
        {
            'name': 'model_Id',
            'in': 'path',
            'required': True,
            'description': '欲查詢的模型ID',
            "schema": {"type": "integer", 'example': 1},
        }
    ],
    'responses': {
        200: {
            'description': '訓練模型狀態資料',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'user_id': {'type': 'integer', 'description': '使用者ID'},
                            'training_file_id': {'type': 'integer', 'description': '訓練文件ID'},
                            'filename': {'type': 'string', 'description': '保存的文件名稱'},
                            'original_file_name': {'type': 'string', 'description': '原始上傳文件名'},
                            'start_train': {'type': 'boolean', 'description': '是否開始訓練'},
                            'is_trained': {'type': 'boolean', 'description': '是否訓練完成'},
                            'file_upload_time': {'type': 'string', 'format': 'date-time', 'description': '文件上傳時間'},
                            'model_id': {'type': 'integer', 'description': '模型ID'},
                            'model_name': {'type': 'string', 'description': '模型名稱'},
                            'model_photo': {'type': 'string', 'description': '模型照片路徑'},
                            'model_anticipation': {'type': 'string', 'description': '模型描述'}
                        }
                    }
                }
            }
        },
        400: {
            'description': '模型ID為必填項或格式錯誤'
        },
        404: {
            'description': '使用者或模型不存在'
        },
        500: {
            'description': '伺服器錯誤，無法取得模型狀態'
        }
    }
})
def get_model_status(model_Id):
    current_email = get_jwt_identity()

    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    
    model_exists = TrainedModelRepo.is_model_id_exists(model_Id)
    if not model_exists:
        return jsonify({"error": "Model ID not found in database"}), 404

    try:
        # 查詢使用者的第一個已訓練模型
        trained_model_status = TrainedModelRepo.find_trainedmodel_by_user_id(user.id)
        if not trained_model_status:
            return jsonify({"message": "No trained model found for this user."}), 404

        # 查詢相關的訓練檔案
        training_file_status = TrainingFileRepo.find_first_training_file_by_user_and_model_id(user.id, model_Id)
        if not training_file_status:
            return jsonify({"message": "No training files found for this user."}), 404

    except Exception as e:
        logging.error(f"Error retrieving training files or trained model for user {user}: {e}")
        return (
            jsonify({"message": "An error occurred while fetching training files or trained model."}),
            500,
        )

    return (
        jsonify(
            {
                "user_id": training_file_status.user_id,
                "training_file_id": training_file_status.id,
                "filename": training_file_status.filename,
                "original_file_name": training_file_status.original_file_name,
                "start_train": training_file_status.start_train,
                "is_trained": training_file_status.is_trained,
                "file_upload_time": training_file_status.upload_time.strftime("%Y-%m-%d %H:%M:%S"),
                "model_id": trained_model_status.id,
                "model_name": trained_model_status.modelname,
                "model_photo": trained_model_status.modelphoto,
                "model_anticipation": trained_model_status.anticipation,
            }
        ),
        200,
    )