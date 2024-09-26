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

FILE_DIRECTORY = os.path.abspath("..\\user_info_file")

def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

@userinfo_bp.post("/user/upload_photo")
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
def upload_photo():
    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "Forbidden"}), 403

    user_id = user_info.get("user_Id")
    if not user_id:
        return jsonify({"error": "Invalid user ID"}), 400

    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 jpg, jpeg, png
    if file and allowed_file(file.filename, ["jpg", "jpeg", "png"]):
        
        # 確認目錄是否存在，若不存在則創建目錄
        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = UserInfoRepo.find_user_info_by_user_id(
            user_id=user_id
        )
        
        user_folder = os.path.join(FILE_DIRECTORY, user_id)
        
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file:
            os.remove(os.path.join(user_folder, current_file.filename))
            UserInfoRepo.delete_user_info_by_user_id(user_id)
            
        # 儲存檔案
        saved_file = UserInfoRepo.create_user_info(
            user_id=user_id, filename=file.filename
        )
        if not saved_file:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )
        
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        file.save(os.path.join(user_folder, saved_file.filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only png, jpg, jpeg files are allowed."}),
            400,
        )

