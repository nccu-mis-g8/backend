from flask import Blueprint, request, Response, jsonify
from flasgger import swag_from
import logging
import json

from repository.userinfo_repo import UserInfoRepo
from repository.userinfo_repo import UserInfoRepo
from requests.exceptions import RequestException
import os

userinfo_bp = Blueprint("userinfo", __name__)
logger = logging.getLogger(__name__)

FILE_DIRECTORY = "..\\user_info_file"

def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

@userinfo_bp.post("/user/upload")
@swag_from({
        "tags": ["UserInfo"],
        "description": "此API 用於上傳使用者頭貼 (JPG, JPEG, PNG)",
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
                "description": "The image file to upload",
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
def upload_userinfo():
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
    if file and allowed_file(file.filename, ["jpg", "jpeg", "png"]):
        # 確認目錄是否存在，若不存在則創建目錄

        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = UserInfoRepo.find_user_info_by_user_id(
            user_id=user_id
        )
        is_renew = False  # 是否是覆蓋舊的
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file is not None:
            os.remove(os.path.join(FILE_DIRECTORY, current_file.filename))
            user_info = UserInfoRepo.delete_user_info_by_user_id(user_id)
            is_renew = True
        # 儲存檔案
        saved_file = UserInfoRepo.create_user_info(
            user_id=user_id, filename=file.filename
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

