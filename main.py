from flask import Flask, jsonify, request
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity, create_refresh_token
)
from datetime import timedelta


app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = 'g8backend'  #key之後要改隨機的或複雜一點的
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=1)  # access token expiration(先設1分鐘測試)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(minutes=1)  # refresh token expiration(先設1分鐘測試)
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


if __name__ == '__main__':
    app.run(debug=True)
