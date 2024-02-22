from flask import *
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId

# 建立Application物件，靜態檔案處理設定
app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)

# 設定Session金鑰
app.secret_key="nccumisg8"

uri = "mongodb+srv://root:root123@flask.egpbsbx.mongodb.net/?retryWrites=true&w=majority&appName=flask"
# 連線到MongoDB
client = MongoClient(uri, server_api=ServerApi('1'))






app.run()