from flask import *
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity, create_refresh_token, get_jwt
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta, datetime
# from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'g8backend'  #key之後要改隨機的或複雜一點的
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=5)  # access token expiration
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)  # refresh token expiration

# connect db
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False #不做追蹤對象的修改(減少效能損耗)
# 資料庫連線:"postgresql://postgres:[資料庫密碼]@localhost:5432/[資料庫名字]"
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:andy0329@localhost:5432/nccu-mis-g8"

db = SQLAlchemy(app)
jwt = JWTManager(app)
# bcrypt = Bcrypt(app)

class TokenBlocklist(db.Model):
    __tablename__ = 'tokenBlockList'
    id = db.Column(db.Integer(), primary_key=True)
    jti = db.Column(db.String(), nullable=True)
    create_at = db.Column(db.DateTime(), default=datetime.utcnow)

    def __repr__(self):
        return f"<Token {self.jti}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()

@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    
    token = db.session.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).scalar()

    return token is not None

class User(db.Model):
    __tablename__ = 'user'
    username = db.Column(db.String(50), primary_key=True)
    password = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def __init__(self, username, password, role="User"):
        self.username = username
        self.password = generate_password_hash(password)
        self.role = role
        
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
# define table
@app.before_request
def create_tables():
    db.create_all()

# 註冊
@app.route('/register', methods=["POST"])
def register():
    # 從前端接收註冊資訊
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    new_user = User(username, password)
    # 確認此帳號有無被註冊過
    user = db.session.query(User).filter(User.username == username).first()
    if user is not None:
        return jsonify(message='此帳號已被使用'), 400
    # 若沒有則將資料加入資料庫 (完成註冊)
    db.session.add(new_user)
    db.session.commit()
    
    access_token = create_access_token(identity=username)

    return jsonify(message='註冊成功', access_token=access_token)

# 登入
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    # 確認是否登入成功
    user = db.session.query(User).filter(User.username == username).first()
    if user is None or not user.check_password(password):
        return jsonify(message='帳號或密碼錯誤'), 401
    
    # 登入成功，生成 JWT Access Token 並返回給客戶端
    access_token = create_access_token(identity=username)
    refresh_token = create_refresh_token(identity=username)

    return jsonify(message='登入成功', access_token=access_token, refresh_token=refresh_token), 200

# 使用 Refresh Token 的 route，用來刷新 Access Token
@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token)


# 登出
@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jwt = get_jwt()
    jti = jwt['jti']
    token_type = jwt['type']
    tbList = TokenBlocklist(jti=jti)
    tbList.save()
    
    return jsonify({"message": f"{token_type} token revoked successfully"}) , 200


# 刪除帳號
@app.route('/delete',  methods=['POST'])
@jwt_required()
def delete():
    current_user = get_jwt_identity()

    # 在資料庫中刪除user
    try:
        user_to_delete = User.query.filter_by(username=current_user).first()
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
            return jsonify(message='帳號刪除成功'), 200
        else:
            return jsonify(message='找不到要刪除的帳號'), 404
    except Exception as e:
        return jsonify(message=f'帳號刪除失敗: {str(e)}'), 500

if __name__ == '__main__':
    app.run(debug=True)

# 主頁
# @app.route("/", methods=["GET"])
# def index():
#     return render_template("index.html")

# 錯誤頁面
# /error?msg=錯誤訊息
# @app.route("/error", methods=["GET"])
# def error():
#     msg = request.args.get("msg", "error occurred")
#     return render_template("error.html", msg=msg)

# 登入成功頁面
# @app.route("/member", methods=["GET"])
# def member():
#     if "account" in session:
#         return render_template("member.html")
#     else:
#         return redirect("/")
