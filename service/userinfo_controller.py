import os
import mimetypes
from flask import Blueprint, request, jsonify, send_file
from flasgger import swag_from
import logging
import json

from flask_jwt_extended import get_jwt_identity, jwt_required

from repository.trainedmodel_repo import TrainedModelRepo
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
    此 API 用於上傳使用者頭貼，支援格式為 JPG, JPEG, PNG。

    Input:
    - `Authorization` header 必須包含 Bearer token 以進行身份驗證。
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
                    "error": "No file provided",
                    "error": "File type not allowed. Only png, jpg, jpeg files are allowed."
                }
            },
        },
        403: {
            "description": "Forbidden request due to missing or invalid user information",
            "examples": {"application/json": {"error": "Forbidden"}},
        },
        404: {
            "description": "User not found",
            "examples": {"application/json": {"error": "User ID not found"}},
        },
        500: {
            "description": "Internal server error occurred while processing the request",
            "examples": {"application/json": {"error": "Unable to create file.", "error": "Internal Server Error"}},
        },
    },
})
def upload_photo():
    current_email = get_jwt_identity()
    
    # 從資料庫中查詢使用者
    user = User.get_user_by_email(current_email)
    if user is None:
        return jsonify(message="使用者不存在"), 404
    
    user_exists = User.is_user_id_exists(user.id)
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
            user_id=user.id
        )
        
        user_folder = os.path.join(FILE_DIRECTORY, str(user.id))
        
        # 上傳新的覆蓋舊的，把舊的file實體刪除
        if current_file:
            os.remove(os.path.join(user_folder, current_file.photoname))
            UserPhotoRepo.delete_user_photo_by_user_id(user.id)
            
        # 儲存檔案
        saved_file = UserPhotoRepo.create_user_photo(
            user_id=user.id, photoname=file.filename
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
        default_image_path = os.path.join(FILE_DIRECTORY, 'default', "avatar.png")
        if os.path.exists(default_image_path):
            return send_file(default_image_path, mimetype="image/png")
        else:
            return jsonify({"error": "User or photo not found"}), 404

    
    user_folder = os.path.join(FILE_DIRECTORY, str(user_id))
    file_path = os.path.join(user_folder, user_info.photoname)

    # 檢查照片檔案是否存在
    if not os.path.exists(file_path):
        # 如果檔案不存在，也回傳預設圖片
        default_image_path = os.path.join(FILE_DIRECTORY, 'default', "avatar.png")
        if os.path.exists(default_image_path):
            return send_file(default_image_path, mimetype="image/png")
        else:
            return jsonify({"error": "User or photo not found"}), 404

    # 傳回使用者的圖片檔案
    return send_file(file_path, mimetype=mimetypes.guess_type(file_path)[0])

@userinfo_bp.get("/images/<photoname>")
@jwt_required()
@swag_from(
    {
        "tags": ["UserInfo"],
        "description": """
        此API 拿取照片。

        Input:
        - photopath: 欲獲取的照片路徑
        
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
                "name": "photoname",
                "in": "path",
                "type": "string",
                "required": True,
                "description": "User information in JSON format",
            }
        ],
        "responses": {
            "200": {
                "description": "成功回傳使用者頭像",
                "content": {
                    "image/jpeg": {},
                    "image/png": {},
                    "image/jpg": {}
                }
            },
            "400": {
                "description": "Bad request due to missing file or wrong file type",
                "examples": {
                    "application/json": {"error": "Bad request - invalid path"}
                },
            },
            "404": {
                "description": "Image not found",
                "examples": {"application/json": {"error": "Image not found"}},
            },
            "500": {
                "description": "Internal Error",
                "examples": {"application/json": {"error": "Internal Server Error"}},
            },
        },
    }
)
def get_image(photoname):
    current_email = get_jwt_identity()
    id = User.get_user_by_email(current_email).id

    if(photoname == 'avatar.png'):
        file_path = os.path.join(FILE_DIRECTORY, 'default',photoname)
    else:
        file_path = os.path.join(FILE_DIRECTORY, str(id),photoname)
    print(file_path)
    if not os.path.exists(file_path):
        # 如果檔案不存在，也回傳預設圖片
        default_image_path = os.path.join(FILE_DIRECTORY, 'default',"avatar.png")
        if os.path.exists(default_image_path):
            return send_file(default_image_path, mimetype="image/png")
        else:
            return jsonify({"error": "User or photo not found"}), 404

    # 傳回使用者的圖片檔案
    return send_file(file_path, mimetype=mimetypes.guess_type(file_path)[0])

@userinfo_bp.post("/user/create_model")
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
            "name": "model_name",
            "in": "formData",
            "required": True,
            "type": "string",
            "description": "model_name",
            "example": "model_name"
        },
        {
            "name": "anticipation",
            "in": "formData",
            "required": True,
            "type": "string",
            "description": "anticipation",
            "example": "anticipation"
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
            "description": "model created successfully",
            "examples": {
                "application/json": {"message": "model created successfully"}
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
def create_model():
    current_email = get_jwt_identity()
    user_id = User.get_user_by_email(current_email).id
    
    if user_id is None:
        return jsonify({"error": "User ID not found"}), 404

    model_name = request.form.get("model_name")
    if model_name is None or model_name == "":
        return jsonify({"error": "model_name is required"}), 400
    
    anticipation = request.form.get("anticipation")
    if anticipation == "":
        anticipation = None

    # 檢查是否有檔案
    if "file" not in request.files:
        model_photo = None

    else:
        file = request.files["file"]
        # 檢查檔案名稱是否存在
        if file.filename == "":
            return jsonify({"error": "No file provided"}), 400
        model_photo = file.filename
        # 確認檔案類型是否為 jpg, jpeg, png
        if file and allowed_file(file.filename, ["jpg", "jpeg", "png"]):
            
            # 檢查並創建檔案目錄
            if not os.path.exists(FILE_DIRECTORY):
                os.makedirs(FILE_DIRECTORY)
            
            user_folder = os.path.join(FILE_DIRECTORY, str(user_id))
                            
            # 儲存檔案
            saved_model = TrainedModelRepo.create_trainedmodel(
                user_id=user_id, modelname=model_name, modelphoto=model_photo, anticipation=anticipation
            )
            if not saved_model:
                return (
                    jsonify({"error": "Unable to create file."}),
                    500,
                )
            
            if not os.path.exists(user_folder):
                os.makedirs(user_folder)

            file.save(os.path.join(user_folder, saved_model.modelphoto))
            return jsonify({"message": "model created successfully"}), 200
        else:
            return (
                jsonify({"error": "File type not allowed. Only png, jpg, jpeg files are allowed."}),
                400,
            )

