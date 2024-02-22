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

# 首頁(註冊、登入)
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# 登入成功頁面
@app.route("/member", methods=["GET"])
def member():
    return render_template("member.html")

# 錯誤頁面
# /error?msg=錯誤訊息
@app.route("/error", methods=["GET"])
def error():
    msg = request.args.get("msg", "error occurred")
    return render_template("error.html", msg=msg)

# 註冊
@app.route("/signup", methods=["POST"])
def signup():
    account = request.form["account"]
    password = request.form["password"]
    # 資料庫處理
    collection = db.user
    # 確認此帳號有無被註冊過
    result = collection.find_one({
        "account": account
    })
    if result != None:
        return redirect("/error?msg=此帳號已被使用")
    # 若沒有則將資料加入資料庫 (完成註冊)
    collection.insert_one({
        "account": account,
        "password": password
    })
    return redirect("/") # 重新導向回首頁

@app.route("/signin")
def signin():
    account = request.form["account"]
    password = request.form["password"]
    # 資料庫處理
    collection = db.user
    result = collection.find_one({
        "$and":[
            {"account": account},
            {"password": password}
        ]
    })

app.run()