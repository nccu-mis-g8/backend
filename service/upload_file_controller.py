from werkzeug.datastructures import FileStorage
from utils.sftp import SFTPClient
import json
import os
from flask import jsonify, request
from werkzeug.utils import secure_filename


@app.route("/upload", methods=["post"])
def upload():
    file: FileStorage | None = request.files.get("file")
    user_info = request.data

    user_info = request.form.get("user_info")
    if user_info:
        user_info = json.loads(user_info)
    else:
        return jsonify({"error": "No user info provided"}), 400

    # 獲取 userId
    user_id = user_info.get("userId")
    print(user_id)
    if not user_id:
        return jsonify({"error": "userId not provided"}), 400
    if not file:
        return jsonify({"error": "file not provided"}), 400
    filename = secure_filename(file.filename)
    file.save(os.path.join("train_model", filename))

    # private key 再自己設定
    sftp = SFTPClient("127.0.0.1", 22, "User", "./id_rsa")

    # 檢查該user已有沒有自己的資料夾
    is_folder_exists = sftp.check_is_folder_exists(user_id)
    if not is_folder_exists:
        sftp.create_directory(user_id)

    # csv存檔位置
    sftp.upload_file(
        local_file=f"./train_model/{filename}",
        remote_file=f"./{user_id}/{user_id}_training_data_flw.csv",
    )
    sftp.quit()

    # response我不知道要傳啥
    return
