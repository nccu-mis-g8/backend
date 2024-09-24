from flask import (
    Blueprint,
    request,
    jsonify,
)
from flasgger import swag_from
import json
import os
import logging

from repository.trainingfile_repo import TrainingFileRepo

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


# only allow to upload csv file
ALLOWED_EXTENSIONS = set(["csv"])
FILE_DIRECTORY = "..\\training_file"


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@utils_bp.post("/user/upload_file")
@swag_from(
    {
        "tags": ["Utils"],
        "description": "此API 用於上傳 CSV 檔案",
        "parameters": [
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
def upload_file():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    # 獲取 userId
    user_id = user_info.get("user_Id")

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 csv
    if file and allowed_file(file.filename):
        # 確認目錄是否存在，若不存在則創建目錄

        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(user_id, file.filename)
        if saved_file is None:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )
        file.save(os.path.join(FILE_DIRECTORY, saved_file.filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only CSV files are allowed."}),
            400,
        )
    
@utils_bp.get("/user/get_files/<int:id>")
@swag_from(
    {
        "tags": ["Utils"],
        "description": "此API 用獲取使用者已訓練過的檔案名稱或是未訓練過的檔案名稱",
        "parameters": [
            {
                "name": "id",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "User id ",
            },
        ],
        "responses": {
            "200": {
                "description": "File retrieved successfully",
                "examples": {
                    "application/json": {"message": "File retrieved successfully"}
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
def get_files(id):
   
    user_id = id
    trained_files = TrainingFileRepo.find_trained_file_by_user_id(user_id)
    not_trained_files = TrainingFileRepo.find_not_trained_file_by_user_id(user_id)
    
    trained_files = [file.filename for file in trained_files]
    not_trained_files = [file.filename for file in not_trained_files]
    return jsonify({"trained_file_name": trained_files},{"not_trained_file_name": not_trained_files}), 200