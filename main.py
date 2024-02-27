from flask import *
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity, create_refresh_token
)
from datetime import timedelta

from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'g8backend'  #key之後要改隨機的或複雜一點的
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=1)  # access token expiration(先設1分鐘測試)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(minutes=1)  # refresh token expiration(先設1分鐘測試)

# 設定Session金鑰
app.secret_key="nccumisg8"

# connect db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #不做追蹤對象的修改(減少效能損耗)
# 連線 (測試用: 記得改成自己的密碼&DB name)
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:root123@localhost:5432/flask"

db = SQLAlchemy(app)


jwt = JWTManager(app)

class User:
    def __init__(self, user_id, username, password):
        self.id = user_id
        self.username = username
        self.password = password

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    # 測試用
    if username == 'andy' and password == '110306059':
        access_token = create_access_token(identity=username)
        refresh_token = create_refresh_token(identity=username)
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    else:
        return jsonify(message='Invalid credentials'), 401

# 用戶在發出request，要提供有效的jwt token
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify(user_identity=current_user), 200

# refresh token
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    reftoken = {
        'access_token': create_access_token(identity=current_user)
    }
    return jsonify(reftoken), 200

#---------------------------------------------------------------------------------#
#create the table we define
@app.route('/initdb')
def dbtest():
    #test if db really can run
    if db.engine.dialect.has_table(db.engine, "user"):
        print("資料表 'user' 存在")
    else:
        print("資料表 'user' 不存在")
    db.create_all()
    return 'Success'

class User(db.Model):
    __tablename__ = 'users'
    account = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.String(50), nullable=False)

    def __init__(self, account, password):
        self.account = account
        self.password = password

# 首頁(註冊、登入)
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

# 登入成功頁面
@app.route("/member", methods=["GET"])
def member():
    if "account" in session:
        return render_template("member.html")
    else:
        return redirect("/")

# 錯誤頁面
# /error?msg=錯誤訊息
@app.route("/error", methods=["GET"])
def error():
    msg = request.args.get("msg", "error occurred")
    return render_template("error.html", msg=msg)

# 註冊
@app.route('/signup', methods=["POST"])
def register():
    # 從前端接收註冊資訊
    account = request.form["account"]
    password = request.form["password"]
    new_user = User(account, password)
    # 確認此帳號有無被註冊過
    result = db.session.query(User).filter(User.account == account).first()
    if result != None:
        return redirect("/error?msg=此帳號已被使用")
    # 若沒有則將資料加入資料庫 (完成註冊)
    db.session.add(new_user)
    db.session.commit()

    return redirect("/") # 重新導向回首頁

# 登入
@app.route("/signin", methods=["POST"])
def signin():
    account = request.form["account"]
    password = request.form["password"]
    # 確認是否登入成功
    result = db.session.query(User).filter(User.account == account, User.password == password).first()
    if result == None:
        return redirect("/error?msg=帳號或密碼錯誤")
    # 登入成功
    # 在Session紀錄會員資訊，並導向到登入成功頁面
    session["account"] = result.account
    return redirect("/member")

# 登出
@app.route("/signout", methods=["GET"])
def signout():
    # 移除Session中的會員資訊，並導回首頁
    del session["account"]
    return redirect("/")

@app.route('/deleteUser')
def delete():
    # Delete data
    query = User.query.filter_by(account=session["account"]).first()
    db.session.delete(query)
    db.session.commit()
    del session["account"]

    return redirect("/")


if __name__ == '__main__':
    app.run(debug=True)
