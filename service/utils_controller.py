from flask import (
    Blueprint,
    request,
    jsonify,
)
from flasgger import swag_from
from repository.trainingfile_repo import TrainingFileRepo
from models.user import User
import json
import os
import logging
import linetxt_to_llama

utils_bp = Blueprint("utils", __name__)
logger = logging.getLogger(__name__)


FILE_DIRECTORY = "..\\training_file"


def allowed_file(filename, extension):
    return "." in filename and filename.rsplit(".", 1)[1].lower() == extension


@utils_bp.post("/user/upload_csv_file")
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
def upload_csv_file():
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
            os.remove(current_file.filename)
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

@utils_bp.get('/user/training_files/<int:user_id>')
@swag_from({
    "tags": ["Utils"],
    'description': '此 api 用於拿到指定 user_id 的 training file',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': 'The ID of the user whose training file is being retrieved.',
            'schema': {
                'type': 'integer',
                'example': 1
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'A training file object for the user',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer', 'example': 1},
                    'user_id': {'type': 'integer', 'example': 123},
                    'filename': {'type': 'string', 'example': 'file.csv'},
                    'original_file_name': {'type': 'string', 'example': 'my_file.csv'},
                    'is_trained': {'type': 'boolean', 'example': False},
                    'upload_time': {'type': 'string', 'example': '2024-09-26 15:30:00'}
                }
            }
        },
        '400': {
            'description': 'Invalid user_id',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'Invalid user_id'}
                }
            }
        },
        '404': {
            'description': 'No training files found for this user',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'No training files found for this user.'}
                }
            }
        },
        '500': {
            'description': 'Server error while fetching training files',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string', 'example': 'An error occurred while fetching training files.'}
                }
            }
        }
    }
})
def get_user_training_files(user_id):
    
    # 確認使用者是否存在
    user_exists = User.is_user_id_exists(user_id)
    if not user_exists:
        return jsonify({"error": "User ID not found"}), 404
    
    try:
        training_file = TrainingFileRepo.find_first_training_file_by_user_id(user_id)
        
        if not training_file:
            return jsonify({"message": "No training files found for this user."}), 404
        
    except Exception as e:
        logging.error(f"Error retrieving training files for user {user_id}: {e}")
        return jsonify({"message": "An error occurred while fetching training files."}), 500

    return jsonify({
        "id": training_file.id,
        "user_id": training_file.user_id,
        "filename": training_file.filename,
        "original_file_name": training_file.original_file_name,
        "is_trained": training_file.is_trained,
        "upload_time": training_file.upload_time.strftime('%Y-%m-%d %H:%M:%S')
    }), 200
    
    
@utils_bp.post('/user/upload_txt_file')
@swag_from({
    "tags": ["Utils"],
    'description': '此 api 用於上傳 txt file，然後轉為 csv fil儲存',
    'parameters': [
        {
            'name': 'user_info',
            'in': 'formData',
            'description': 'JSON string containing user_Id and master_name',
            'required': True,
            'type': 'string',
            'example': '{"user_Id": "12345", "master_name": "John"}'
        },
        {
            'name': 'file',
            'in': 'formData',
            'description': 'TXT file to be uploaded',
            'required': True,
            'type': 'file'
        }
    ],
    'responses': {
        200: {
            'description': 'File uploaded successfully',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': 'File uploaded successfully'
                    }
                }
            }
        },
        400: {
            'description': 'Bad request',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': 'user_Id or master_name is missing'
                    }
                }
            }
        },
        403: {
            'description': 'Forbidden: User info is missing',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': 'Forbidden'
                    }
                }
            }
        },
        404: {
            'description': 'File not found',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': 'File not found: /path/to/file'
                    }
                }
            }
        },
        500: {
            'description': 'Internal server error',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': 'File processing error: error message'
                    }
                }
            }
        }
    }
})
def upload_txt_file():
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
    master_name = user_info.get('master_name')
    
    if not user_id or not master_name:
        return jsonify({"error": "user_Id or master_name is missing"}), 400

    # 確認 request 中是否有檔案
    if "file" not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files.get('file')
    
    # 確認檔案是否存在
    if file.filename == "":
        return jsonify({"error": "No file provided"}), 400

    # 確認檔案類型是否為 txt
    if file and allowed_file(file.filename, "txt"):
        # 確認目錄是否存在，若不存在則創建目錄
        if not os.path.exists(FILE_DIRECTORY):
            os.makedirs(FILE_DIRECTORY)

        # 處理 line chat 的文件
        processor = linetxt_to_llama.LineChatProcessor(output_name=user_id, master_name=master_name, data_dir=FILE_DIRECTORY)
        try:
            csv_file_name = processor.process(file)  # 假設 process 方法需要文件來處理
            print(csv_file_name)
        except Exception as e:
            return jsonify({"error": f"File processing error: {str(e)}"}), 500

        # 確認是否已有未完成的訓練文件，並刪除
        current_file = TrainingFileRepo.find_first_training_file_by_user_id(user_id=user_id)
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
        saved_file = TrainingFileRepo.create_trainingfile(user_id=user_id, filename=csv_file_name, original_file_name=file.filename)
        if saved_file is None:
            return jsonify({"error": "Unable to create file."}), 500

        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return jsonify({"error": "File type not allowed. Only TXT files are allowed."}), 400
        
    
