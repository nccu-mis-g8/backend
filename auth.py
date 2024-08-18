from datetime import timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required, 
    create_access_token,
    create_refresh_token, 
    get_jwt_identity,  
)
from models import User, RefreshToken
from sqlalchemy.exc import SQLAlchemyError
import re
import logging

auth_bp = Blueprint("auth", __name__)

logger = logging.getLogger(__name__)

@auth_bp.post("/register")
def register():
    """
    用戶註冊

    Input:
        - JSON 格式的請求，包含 'username' 和 'password' 字段。
    
    Steps:
        1. 檢查用戶名和密碼是否提供且有效。
        2. 檢查用戶名是否已被使用。
        3. 如果所有檢查通過，創建新的用戶並保存到資料庫。
        4. 處理可能的資料庫錯誤或其他異常。

    Returns:
        - JSON 格式的回應消息:
            - 註冊成功: 包含成功消息和新用戶的一些基本資訊。
            - 註冊失敗: 包含錯誤消息和相應的 HTTP status code。
    """
    try:
        # 從請求中獲取用戶名和密碼
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        
        # 檢查用戶名和密碼是否存在且有效
        if not username or not password:
            return jsonify(message='使用者名稱和密碼不可為空'), 400

        # 檢查用戶名是否符合規範
        if not is_valid_username(username):
            return jsonify(message='使用者名稱不符合規範'), 400

        # 檢查密碼強度
        if not is_strong_password(password):
            return jsonify(message='密碼必須至少包含8個字符，並包含字母和數字'), 400
            
        # 創建新的用戶實例
        new_user = User(username, password)

        # 檢查用戶名是否已存在
        user = User.get_user_by_username(username)
        if user is not None:
            return jsonify(message='此帳號已被使用'), 400
        
        # 保存新用戶到數據庫
        new_user.save()

        # 返回成功消息和新用戶資訊
        return jsonify(message='註冊成功', username=new_user.username)
    
    except SQLAlchemyError as e:
        # 記錄資料庫錯誤並返回錯誤消息
        logger.error(f"Database error: {e}")
        return jsonify(message='資料庫錯誤，請稍後再試'), 500
    except Exception as e:
        # 記錄一般錯誤並返回錯誤消息
        logger.error(f"Registration failed: {e}")
        return jsonify(message=f'註冊失敗: {str(e)}'), 500


@auth_bp.post("/login")
def login():
    """
    用戶登入

    Input:
    - 期望接收到包含 'username' 和 'password' 字段的 JSON 請求。

    Steps:
    1. 驗證用戶名和密碼是否存在。
    2. 使用提供的用戶名從數據庫中檢索用戶。
    3. 將輸入的密碼與存儲的哈希密碼進行驗證。
    4. 如果身份驗證成功，生成並返回 access token 和 refresh token。
    5. 處理潛在錯誤並返回適當的 HTTP 狀態碼。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回成功消息、access token 和 refresh token。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """
    try:
        username = request.json.get('username')
        password = request.json.get('password')

        # 檢查是否提供了用戶名和密碼
        if not username or not password:
            return jsonify(message='使用者名稱和密碼不可為空'), 400

        # 從數據庫中檢索用戶
        user = User.get_user_by_username(username)
        if user is None or not user.check_password(password):
            return jsonify(message='帳號或密碼錯誤'), 401
        
        RefreshToken.delete_revoked_tokens(user.id)

        # 成功登入時生成 token
        access_token = create_access_token(identity=username, expires_delta=timedelta(minutes=30))
        refresh_token = create_refresh_token(identity=username, expires_delta=timedelta(days=7))
        
        new_refresh_token = RefreshToken(
            user_id=user.id,  # Use the user ID from the User model
            token=refresh_token,
        )
        
        new_refresh_token.save()

        return jsonify(message='登入成功', access_token=access_token, refresh_token=refresh_token), 200

    except SQLAlchemyError as e:
        # 處理與數據庫相關的錯誤
        logger.error(f"資料庫錯誤: {str(e)}")
        return jsonify(message='資料庫錯誤，請稍後再試'), 500

    except Exception as e:
        # 處理其他潛在的異常
        logger.error(f"登入過程中出現錯誤: {str(e)}")
        return jsonify(message=f'登入失敗: {str(e)}'), 500


@auth_bp.post('/refresh')
@jwt_required(refresh=True)
def refresh():
    """
    使用 Refresh Token 刷新 Access Token。

    Steps:
    1. 使用裝飾器 `@jwt_required(refresh=True)` 驗證請求中的 Refresh Token。
    2. 獲取當前用戶的身份（即 `current_user`）。
    3. 為當前用戶生成新的 Access Token。
    4. 返回新的 Access Token 給客戶端。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回新的 Access Token。
      - 失敗時：由 `@jwt_required` 裝飾器自動處理，通常會返回 401 或 422 錯誤。
    """
    try:
        # 獲取當前使用者身份
        current_user = get_jwt_identity()
        user = User.get_user_by_username(current_user)
        # jti = get_jwt()["jti"]
        # print(jti)
        # 从请求中获取 Refresh Token
        refresh_token = request.headers.get('Authorization').split(" ")[1]
        
        # 從資料庫查找這個 Refresh Token
        stored_token = RefreshToken.find_by_token_and_user(refresh_token, user.id)
        
        if not stored_token or stored_token.revoked:
            return jsonify(message='Refresh Token 已失效或已撤銷'), 401
        
        # 為當前使用者生成新的 Access Token
        new_access_token = create_access_token(identity=current_user)

        # 返回新的 Access Token
        return jsonify(access_token=new_access_token), 200

    except Exception as e:
        # 處理可能發生的異常，並記錄錯誤信息
        logger.error(f"刷新 Access Token 過程錯誤: {str(e)}")
        return jsonify(message=f'刷新 Access Token 失敗: {str(e)}'), 500


@auth_bp.post('/logout')
@jwt_required()
def logout():
    """
    登出並且撤銷當前的 refresh token。

    Steps:
    1. 獲取當前使用者的身份。
    2. 根據身份從資料庫中檢索對應的使用者。
    3. 從資料庫查找當前使用者的 refresh token。
    4. 如果找到 refresh token 且尚未被撤銷，將其標記為已撤銷。
    5. 返回成功的登出消息。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回登出成功的消息。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """
    try:
        # 獲取當前用戶的身份
        current_user = get_jwt_identity()
        user = User.get_user_by_username(current_user)
        
        # 從資料庫查找對應的 Refresh Token
        stored_token = RefreshToken.find_by_userId(user.id)

        if stored_token and not stored_token.revoked:
            stored_token.revoke()

        return jsonify(message='登出成功'), 200
    
    except Exception as e:
        logger.error(f"登出過程錯誤: {str(e)}")
        return jsonify(message=f'登出失敗: {str(e)}'), 500


@auth_bp.post('/delete')
@jwt_required()
def delete():
    """
    刪除目前登入用戶的帳號。

    Steps:
    1. 驗證請求中的 Access Token，確保用戶已登入。
    2. 根據目前用戶的身份獲取用戶資訊。
    3. 如果找到對應的用戶，從資料庫刪除該用戶。
    4. 返回成功或失敗的訊息給客戶端。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回 "帳號刪除成功" 訊息和 HTTP 200 狀態碼。
      - 失敗時：返回錯誤訊息和相應的 HTTP 狀態碼。
    """
    current_user = get_jwt_identity()

    try:
        user_to_delete = User.get_user_by_username(current_user)
        if user_to_delete:
            try:
                # 刪除用戶並提交變更
                User.delete(user_to_delete)
                logger.info(f"用戶 {current_user} 帳號刪除成功")
                return jsonify(message='帳號刪除成功'), 200
            except Exception as e:
                logger.error(f"刪除用戶 {current_user} 帳號時發生錯誤: {str(e)}")
                return jsonify(message=f'帳號刪除失敗: {str(e)}'), 500
        else:
            logger.warning(f"用戶 {current_user} 帳號刪除失敗：帳號不存在")
            return jsonify(message='找不到要刪除的帳號'), 404
    except Exception as e:
        logger.error(f"處理帳號刪除請求時發生錯誤: {str(e)}")
        return jsonify(message=f'帳號刪除失敗: {str(e)}'), 500
    
    
def is_valid_username(username):
    """
    驗證用戶名是否合法。

    用戶名應僅包含字母、數字、下劃線、點號和連字符。

    Parameters:
    - username (str): 要驗證的用戶名。

    Returns:
    - bool: 如果用戶名合法，返回 True；否則返回 False。
    """
    return re.match(r'^[a-zA-Z0-9_.-]+$', username)


def is_strong_password(password):
    """
    檢查密碼是否符合規範。

    密碼至少應包含8個字符，並且必須包含字母和數字。

    Parameters:
    - password (str): 要檢查的密碼。

    Returns:
    - bool: 如果密碼符合要求，返回 True；否則返回 False。
    """
    return len(password) >= 8 and re.search(r"[A-Za-z]", password) and re.search(r"[0-9]", password)