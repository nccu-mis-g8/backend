import json
import os
from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename
from extensions import db, jwt
from auth.auth_controller import auth_bp
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint
from flasgger import Swagger
from utils.sftp import SFTPClient
# from train_model.train_model_controller import train_model_bp

load_dotenv()

app = Flask(__name__)
app.config.from_prefixed_env()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SWAGGER'] = {
    'title': 'API Documentation',
    'uiversion': 3,
    'specs': [
        {
            'endpoint': 'swagger',
            'route': '/swagger.json',
            'rule_filter': lambda rule: True,  # all in
            'model_filter': lambda tag: True,  # all in
        }
    ],
    'static_url_path': '/flasgger_static',
    'swagger_ui': True,
    'specs_route': '/swagger/'
}

# initialize
db.init_app(app)
jwt.init_app(app)

# Initialize Swagger
swagger = Swagger(app)

SWAGGER_URL = '/apidocs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = '/swagger.json'  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={'app_name': "Local Test API"}
)

# register necessary blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")
# app.register_blueprint(train_model_bp, url_prefix="/finetune")

# Register Swagger UI blueprint
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

@app.route('/upload', methods=['post'])
def upload():
    file = request.files.get('file')
    user_info = request.data
  
    user_info = request.form.get('user_info')
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "No user info provided"}), 400

    # 獲取 userId
    user_id = user_info.get('userId')
    print(user_id)
    if not user_id:
        return jsonify({"error": "userId not provided"}), 400

    filename = secure_filename(file.filename)
    file.save(os.path.join("train_model",filename))


    #private key 再自己設定
    sftp = SFTPClient('127.0.0.1',22,'User','./id_rsa')

    #檢查該user已有沒有自己的資料夾
    is_folder_exists = sftp.check_is_folder_exists(user_id)
    if(not is_folder_exists):
        sftp.create_directory(user_id)
        
    #csv存檔位置
    sftp.upload_file(local_file=f'./train_model/{filename}',remote_file=f'./{user_id}/{user_id}_training_data_flw.csv')
    sftp.quit()

    # response我不知道要傳啥
    return

# define table
# @app.before_request
# def create_tables():
#     db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
