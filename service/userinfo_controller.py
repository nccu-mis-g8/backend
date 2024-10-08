import os
import mimetypes
from flask import Blueprint, request, jsonify, send_file
from flasgger import swag_from
import logging
import json

from flask_jwt_extended import get_jwt_identity, jwt_required

from repository.userphoto_repo import UserPhotoRepo
from models.user import User

userinfo_bp = Blueprint("userinfo", __name__)
logger = logging.getLogger(__name__)

FILE_DIRECTORY = os.path.abspath("..\\user_photo_file")

def allowed_file(filename, extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in extensions

@userinfo_bp.post("/user/upload_photo")
@jwt_required()
@swag_from({
    "tags": ["UserInfo"],
    "description": """
    此API 用於上傳使用者頭貼，支援格式為 JPG, JPEG, PNG。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
    - user_info: 包含使用者的基本訊息 (例如 user_Id)。
    - file: 要上傳的圖像檔案 (JPG, JPEG, PNG)。
    """,
    "consumes": ["multipart/form-data"],
    "parameters": [
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "description": "Bearer token for authorization",
            "schema": {
                "type": "string",
                "example": "Bearer "
            }
        },
        {
            "name": "user_info",
            "in": "formData",
            "type": "string",
            "required": True,
            "description": "User information in JSON format, containing the user ID",
        },
        {
            "name": "file",
            "in": "formData",
            "type": "file",
            "required": True,
            "description": "The image file to upload (JPG, JPEG, PNG)",
        },
    ],
    "responses": {
        200: {
            "description": "File uploaded successfully",
            "examples": {
                "application/json": {"message": "File uploaded successfully"}
            },
        },
        400: {
            "description": "Bad request due to missing file, wrong file type, or invalid user information",
            "examples": {
                "application/json": {
                    "error": "No file part in the request",
                    "error": "File type not allowed. Only png, jpg, jpeg files are allowed.",
                    "error": "Invalid user_info format"
                }
            },
        },
        403: {
            "description": "Forbidden request due to missing or invalid user information",
            "examples": {"application/json": {"error": "Forbidden"}},
        },
        404: {
            "description": "User ID not found",
            "examples": {"application/json": {"error": "User ID not found"}},
        },
        500: {
            "description": "Internal server error occurred while processing the request",
            "examples": {"application/json": {"error": "Internal Server Error"}},
        },
    },
})
def upload_photo():
    current_email = get_jwt_identity()
    
    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    
    user_info = request.form.get("user_info")
    
    # 檢查是否有 user_info
    if user_info:
        try:
            user_info = json.loads(user_info)
        except ValueError:
            return jsonify({"error": "Invalid user_info format"}), 400
    else:
        return jsonify({"error": "Forbidden"}), 403

    user_id = user_info.get("user_Id")
    print(user_id)
    if not user_id:
        return jsonify({"error": "Invalid user ID"}), 400
    
    user_exists = User.is_user_id_exists(user_id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404

    # 檢查是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400

    file = request.files["file"]

    # 檢查檔案名稱是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 jpg, jpeg, png
    if file and allowed_file(file.filename, ["jpg", "jpeg", "png"]):
        
         # 檢查並創建檔案目錄
        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        current_file = UserPhotoRepo.find_user_photo_by_user_id(
            user_id=user_id
        )
        
        user_folder = os.path.join(FILE_DIRECTORY, str(user_id))
        
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file:
            os.remove(os.path.join(user_folder, current_file.photoname))
            UserPhotoRepo.delete_user_photo_by_user_id(user_id)
            
        # 儲存檔案
        saved_file = UserPhotoRepo.create_user_photo(
            user_id=user_id, photoname=file.filename
        )
        if not saved_file:
            return (
                jsonify({"error": "Unable to create file."}),
                500,
            )
        
        if not os.path.exists(user_folder):
            os.makedirs(user_folder)

        file.save(os.path.join(user_folder, saved_file.photoname))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only png, jpg, jpeg files are allowed."}),
            400,
        )


@userinfo_bp.get("/user/get_photo/<int:user_id>")
@jwt_required()
@swag_from({
    "tags": ["UserInfo"],
    "description": """
    此API用於拿取使用者頭貼，支援格式為 JPG, JPEG, PNG。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
    - user_id: 使用者的唯一ID，用來查找並返回對應的頭像。
    """,
    "parameters": [
        {
            "name": "Authorization",
            "in": "header",
            "required": True,
            "description": "Bearer token for authorization",
            "schema": {
                "type": "string",
                "example": "Bearer "
            }
        },
        {
            "name": "user_id",
            "in": "path",
            "type": "integer",
            "required": True,
            "description": "使用者的唯一ID",
        },
    ],
    "responses": {
        200: {
            "description": "成功回傳使用者頭像",
            "content": {
                "image/jpeg": {},
                "image/png": {},
                "image/jpg": {}
            }
        },
        403: {
            "description": "禁止請求",
            "content": {
                "application/json": {
                    "example": {"error": "Forbidden"}
                }
            }
        },
        404: {
            "description": "使用者或照片找不到",
            "content": {
                "application/json": {
                    "example": {"error": "User ID not found"}
                }
            }
        },
        500: {
            "description": "內部伺服器錯誤",
            "content": {
                "application/json": {
                    "example": {"error": "Internal Server Error"}
                }
            }
        },
    },
})
def get_photo(user_id):
    current_email = get_jwt_identity()
    
    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    
    # 確認使用者是否存在
    user_exists = User.is_user_id_exists(user_id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404
    
    user_info = UserPhotoRepo.find_user_photo_by_user_id(user_id)

    # 如果使用者頭像是 null，則回傳預設圖片
    if not user_info:
        default_image_path = os.path.join(FILE_DIRECTORY, "default_avatar.png")
        if os.path.exists(default_image_path):
            return send_file(default_image_path, mimetype="image/png")
        else:
            return jsonify({"error": "User or photo not found"}), 404

    user_folder = os.path.join(FILE_DIRECTORY, str(user_id))
    file_path = os.path.join(user_folder, user_info.photoname)

    # 檢查照片檔案是否存在
    if not os.path.exists(file_path):
        # 如果檔案不存在，也回傳預設圖片
        default_image_path = os.path.join(FILE_DIRECTORY, "default_avatar.png")
        if os.path.exists(default_image_path):
            return send_file(default_image_path, mimetype="image/png")
        else:
            return jsonify({"error": "User or photo not found"}), 404

    # 傳回使用者的圖片檔案
    return send_file(file_path, mimetype=mimetypes.guess_type(file_path)[0])