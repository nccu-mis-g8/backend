from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, 
    create_access_token,
    create_refresh_token, 
    get_jwt_identity,  
    get_jwt
)
from models import TokenBlocklist, User

auth_bp = Blueprint("auth", __name__)

# 註冊
@auth_bp.post("/register")
def register():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    new_user = User(username, password)

    user = User.get_user_by_username(username)
    if user is not None:
        return jsonify(message='此帳號已被使用'), 400
    
    new_user.save()

    return jsonify(message='註冊成功')

# 登入
@auth_bp.post("/login")
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    
    user = User.get_user_by_username(username)
    if user is None or not user.check_password(password):
        return jsonify(message='帳號或密碼錯誤'), 401
    
    # 登入成功，生成 Access Token 和 Refresh Token並返回給客戶端
    access_token = create_access_token(identity=username)
    refresh_token = create_refresh_token(identity=username)

    return jsonify(message='登入成功', access_token=access_token, refresh_token=refresh_token), 200

# 使用 Refresh Token 的 route，用來刷新 Access Token
@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token)

# 登出
@auth_bp.post('/logout')
@jwt_required()
def logout():
    jwt = get_jwt()
    jti = jwt['jti']
    token_type = jwt['type']
    tbl = TokenBlocklist(jti=jti)
    tbl.save()
    
    return jsonify({"message": f"{token_type} token revoked successfully"}) , 200


# 刪除帳號
@auth_bp.post('/delete')
@jwt_required()
def delete():
    current_user = get_jwt_identity()
    jwt = get_jwt()
    jti = jwt['jti']
    try:
        user_to_delete = User.get_user_by_username(current_user)
        if user_to_delete:
            User.delete(user_to_delete)
            tbl = TokenBlocklist(jti=jti)
            tbl.save()
            return jsonify(message='帳號刪除成功'), 200
        else:
            return jsonify(message='找不到要刪除的帳號'), 404
    except Exception as e:
        return jsonify(message=f'帳號刪除失敗: {str(e)}'), 500