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

# 連線到MongoDB
uri = "mongodb+srv://root:root123@misg8.tjt5wmj.mongodb.net/?retryWrites=true&w=majority&appName=misG8"
client = MongoClient(uri, server_api=ServerApi('1'))
# 選擇操作users資料庫
db = client.users






app.run()