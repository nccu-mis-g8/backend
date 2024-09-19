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


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@utils_bp.post("/user/upload_file")
@swag_from({
    'tags': ['Utils'],
    'description': '此API 用於上傳 CSV 檔案',
    'parameters': [
        {
            'name': 'user_info',
            'in': 'formData',
            'type': 'string',
            'required': True,
            'description': 'User information in JSON format'
        },
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': 'The CSV file to upload'
        }
    ],
    'responses': {
        '200': {
            'description': 'File uploaded successfully',
            'examples': {
                'application/json': {
                    'message': 'File uploaded successfully'
                }
            }
        },
        '400': {
            'description': 'Bad request due to missing file or wrong file type',
            'examples': {
                'application/json': {
                    'error': 'No file part in the request'
                }
            }
        },
        '403': {
            'description': 'Forbidden request',
            'examples': {
                'application/json': {
                    'error': 'Forbidden'
                }
            }
        }
    }
})
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
        file_directory = "../training_file"
        if not os.path.exists(file_directory):
            os.makedirs(file_directory)
            
        # 儲存檔案
        saved_file = TrainingFileRepo.create_trainingfile(user_id)
        file.save(os.path.join(file_directory, saved_file.filename))
        return jsonify({"message": "File uploaded successfully"}), 200
    else:
        return (
            jsonify({"error": "File type not allowed. Only CSV files are allowed."}),
            400,
        )
