from datetime import timedelta
from flasgger import swag_from
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from models.user import User, RefreshToken
from sqlalchemy.exc import SQLAlchemyError
import re
import logging

auth_bp = Blueprint("auth", __name__)
logger = logging.getLogger(__name__)


@auth_bp.post("/register")
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此API用來處理用戶註冊，會檢查用戶名、密碼是否有效，並將新用戶保存至資料庫。

    Input:
        - JSON 格式的請求，包含 'lastname'、'firstname'、'email' 和 'password' 字段。

    Steps:
        1. 檢查所有必須的字段是否提供且有效。
        2. 檢查使用者電子郵件是否已被使用。
        3. 檢查密碼強度。
        4. 如果所有檢查通過，創建新的用戶並保存到資料庫。
        5. 處理可能的資料庫錯誤或其他異常。

    Returns:
        - JSON 格式的回應消息:
            - 註冊成功: 包含成功消息。
            - 註冊失敗: 包含錯誤消息和相應的 HTTP status code。
    """,
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'lastname': {
                        'type': 'string',
                        'description': '用戶姓氏',
                        'example': 'Lin'
                    },
                    'firstname': {
                        'type': 'string',
                        'description': '用戶名字',
                        'example': 'An-An'
                    },
                    'email': {
                        'type': 'string',
                        'description': '用戶電子郵件',
                        'example': 'andy1234@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'description': '用戶密碼，必須至少8個字符，並包含字母和數字',
                        'example': 'andy1234'
                    }
                },
                'required': ['lastname', 'firstname', 'email', 'password']
            }
        }
    ],
    'responses': {
        200: {
            'description': '註冊成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '註冊成功'
                    }
                }
            }
        },
        400: {
            'description': '註冊失敗，輸入無效或電子郵件已存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '此電子郵件已被使用'
                    }
                }
            }
        },
        500: {
            'description': '伺服器錯誤，可能是資料庫異常',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '資料庫錯誤，請稍後再試'
                    }
                }
            }
        }
    }
})
def register():
    try:
        # 從請求中獲取用戶輸入的姓名、電子郵件和密碼
        lastname = request.json.get("lastname", None)
        firstname = request.json.get("firstname", None)
        email = request.json.get("email", None)
        password = request.json.get("password", None)

        # 檢查輸入是否有效
        if not lastname or not firstname or not email or not password:
            return jsonify(message="姓氏、名字、電子郵件和密碼不可為空"), 400

        # 檢查電子郵件是否符合規範
        if not is_valid_email(email):
            return jsonify(message="使用者電子郵件不符合規範"), 400

        # 檢查密碼強度
        if not is_strong_password(password):
            return jsonify(message="密碼必須至少包含8個字符，並包含字母和數字"), 400

        # 創建新的用戶實例
        new_user = User(lastname=lastname, firstname=firstname, email=email, password=password)

        # 檢查電子郵件是否已存在
        user = User.get_user_by_email(email=email)
        if user is not None:
            return jsonify(message="此電子郵件已被使用"), 400

        # 保存新用戶到數據庫
        new_user.save()

        # 返回成功消息
        return jsonify(message="註冊成功"), 200

    except SQLAlchemyError as e:
        # 記錄資料庫錯誤並返回錯誤消息
        logger.error(f"Database error: {e}")
        return jsonify(message="資料庫錯誤，請稍後再試"), 500
    except Exception as e:
        # 記錄一般錯誤並返回錯誤消息
        logger.error(f"Registration failed: {e}")
        return jsonify(message=f"註冊失敗: {str(e)}"), 500


@auth_bp.post("/login")
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此API用來處理用戶登入，會驗證電子郵件和密碼，並返回 access token 和 refresh token。

    Input:
    - 期望接收到包含 'email' 和 'password' 字段的 JSON 請求。

    Steps:
    1. 驗證電子郵件和密碼是否存在。
    2. 使用提供的電子郵件從數據庫中檢索用戶。
    3. 將輸入的密碼與存儲的哈希密碼進行驗證。
    4. 如果身份驗證成功，生成並返回 access token 和 refresh token。
    5. 處理潛在錯誤並返回適當的 HTTP 狀態碼。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回成功消息、用戶資訊、access token 和 refresh token。
      - 失敗時：返回錯誤消息及相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'email': {
                        'type': 'string',
                        'description': '用戶電子郵件',
                        'example': 'andy1234@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'description': '用戶密碼',
                        'example': 'andy1234'
                    }
                },
                'required': ['email', 'password']
            }
        }
    ],
    'responses': {
        200: {
            'description': '登入成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '登入成功'
                    },
                    'user_id': {
                        'type': 'integer',
                        'example': 1
                    },
                    'lastname': {
                        'type': 'string',
                        'example': 'Lin'
                    },
                    'firstname': {
                        'type': 'string',
                        'example': 'An-An'
                    },
                    'email': {
                        'type': 'string',
                        'example': 'andy1234@example.com'
                    },
                    'access_token': {
                        'type': 'string',
                        'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                    },
                    'refresh_token': {
                        'type': 'string',
                        'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                    }
                }
            }
        },
        400: {
            'description': '請求中缺少電子郵件或密碼',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '電子郵件或密碼不可為空'
                    }
                }
            }
        },
        401: {
            'description': '電子郵件或密碼錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '電子郵件或密碼錯誤'
                    }
                }
            }
        },
        500: {
            'description': '伺服器內部錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '資料庫錯誤，請稍後再試'
                    }
                }
            }
        }
    }
})
def login():
    try:
        # 從請求中獲取用戶輸入的電子郵件和密碼
        email = request.json.get("email", None)
        password = request.json.get("password")

        # 檢查是否提供了電子郵件和密碼
        if not email or not password:
            return jsonify(message="電子郵件或密碼不可為空"), 400

        # 從數據庫中檢索用戶
        user = User.get_user_by_email(email=email)
        if user is None or not user.check_password(password):
            return jsonify(message="電子郵件或密碼錯誤"), 401

        # 刪除之前的 refresh token
        RefreshToken.delete_revoked_tokens(user.id)

        # 成功登入時生成 token
        access_token = create_access_token(
            identity=email, expires_delta=timedelta(minutes=30)
        )
        refresh_token = create_refresh_token(
            identity=email, expires_delta=timedelta(days=7)
        )

        # 保存新的 refresh token 到數據庫
        new_refresh_token = RefreshToken(
            user_id=user.id,  # 使用用戶ID
            token=refresh_token,
        )

        new_refresh_token.save()

        return (
            jsonify(
                message="登入成功", 
                user_id=user.id,
                lastname=user.lastname,
                firstname=user.firstname,
                email=user.email,
                access_token=access_token, 
                refresh_token=refresh_token
            ),
            200,
        )

    except SQLAlchemyError as e:
        # 處理與數據庫相關的錯誤
        logger.error(f"資料庫錯誤: {str(e)}")
        return jsonify(message="資料庫錯誤，請稍後再試"), 500

    except Exception as e:
        # 處理其他潛在的異常
        logger.error(f"登入過程中出現錯誤: {str(e)}")
        return jsonify(message=f"登入失敗: {str(e)}"), 500


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此 API 用於使用已驗證的 Refresh Token 來生成新的 Access Token。

    Steps:
    1. 使用裝飾器 `@jwt_required(refresh=True)` 驗證請求中的 Refresh Token。
    2. 獲取當前用戶的身份（即 `current_email`）。
    3. 為當前用戶生成新的 Access Token。
    4. 返回新的 Access Token 給客戶端。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回新的 Access Token。
      - 失敗時：由 `@jwt_required` 裝飾器自動處理，通常會返回 401 或 422 錯誤。
    """,
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Bearer Token，使用者的 Refresh Token，格式為 "Bearer <token>"',
            'example': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        }
    ],
    'responses': {
        200: {
            'description': '成功刷新 Access Token',
            'schema': {
                'type': 'object',
                'properties': {
                    'access_token': {
                        'type': 'string',
                        'description': '新的 Access Token',
                        'example': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
                    }
                }
            }
        },
        401: {
            'description': 'Refresh Token 無效或已撤銷',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': 'Refresh Token 已失效或已撤銷'
                    }
                }
            }
        },
        500: {
            'description': '伺服器內部錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '刷新 Access Token 失敗: 詳細錯誤信息'
                    }
                }
            }
        }
    },
    'security': [
        {
            'Bearer': []
        }
    ]
})
def refresh():
    try:
        # 獲取當前使用者身份
        current_account = get_jwt_identity()
        user = User.get_user_by_account(current_account)
        
        # 從請求中獲取 Refresh Token
        refresh_token = request.headers.get("Authorization").split(" ")[1]

        # 從資料庫查找這個 Refresh Token
        stored_token = RefreshToken.find_by_token_and_user(refresh_token, user.id)

        if not stored_token or stored_token.revoked:
            return jsonify(message="Refresh Token 已失效或已撤銷"), 401

        # 為當前使用者生成新的 Access Token
        new_access_token = create_access_token(identity=current_account)

        # 返回新的 Access Token
        return jsonify(access_token=new_access_token), 200

    except Exception as e:
        # 處理可能發生的異常，並記錄錯誤信息
        logger.error(f"刷新 Access Token 過程錯誤: {str(e)}")
        return jsonify(message=f"刷新 Access Token 失敗: {str(e)}"), 500


@auth_bp.post("/logout")
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此 API 用於當用戶登出時，撤銷與用戶關聯的 Refresh Token 並返回登出成功的訊息。

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
    """,
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Bearer Token，使用者的 Access Token，格式為 "Bearer <token>"',
            'example': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        }
    ],
    'responses': {
        200: {
            'description': '成功登出並撤銷 Refresh Token',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '登出成功'
                    }
                }
            }
        },
        500: {
            'description': '伺服器內部錯誤',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '登出失敗: 詳細錯誤信息'
                    }
                }
            }
        }
    },
    'security': [
        {
            'Bearer': []
        }
    ]
})
def logout():
    try:
        # 獲取當前用戶的身份
        current_account = get_jwt_identity()
        user = User.get_user_by_account(current_account)

        # 從資料庫查找對應的 Refresh Token
        stored_token = RefreshToken.find_by_userId(user.id)

        if stored_token and not stored_token.revoked:
            stored_token.revoke()

        return jsonify(message="登出成功"), 200

    except Exception as e:
        logger.error(f"登出過程錯誤: {str(e)}")
        return jsonify(message=f"登出失敗: {str(e)}"), 500


@auth_bp.post("/delete")
@jwt_required()
@swag_from({
    'tags': ['Authentication'],
    'description': """
    此 API 用於刪除當前登入用戶的帳號，並返回相應的訊息。

    Steps:
    1. 驗證請求中的 Access Token，確保用戶已登入。
    2. 根據目前用戶的身份獲取用戶資訊。
    3. 如果找到對應的用戶，從資料庫刪除該用戶。
    4. 返回成功或失敗的訊息給客戶端。

    Returns:
    - JSON 回應訊息：
      - 成功時：返回 "帳號刪除成功" 訊息和 HTTP 200 狀態碼。
      - 失敗時：返回錯誤訊息和相應的 HTTP 狀態碼。
    """,
    'parameters': [
        {
            'name': 'Authorization',
            'in': 'header',
            'type': 'string',
            'required': True,
            'description': 'Bearer Token，使用者的 Access Token，格式為 "Bearer <token>"',
            'example': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
        }
    ],
    'responses': {
        200: {
            'description': '帳號刪除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '帳號刪除成功'
                    }
                }
            }
        },
        404: {
            'description': '找不到要刪除的帳號',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '找不到要刪除的帳號'
                    }
                }
            }
        },
        500: {
            'description': '伺服器錯誤，帳號刪除失敗',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '帳號刪除失敗: 具體錯誤信息'
                    }
                }
            }
        }
    },
    'security': [
        {
            'Bearer': []
        }
    ],
})
def delete():
    current_account = get_jwt_identity()

    try:
        user_to_delete = User.get_user_by_account(current_account)
        if user_to_delete:
            try:
                # 刪除用戶並提交變更
                User.delete(user_to_delete)
                logger.info(f"用戶 {current_account} 帳號刪除成功")
                return jsonify(message="帳號刪除成功"), 200
            except Exception as e:
                logger.error(f"刪除用戶 {current_account} 帳號時發生錯誤: {str(e)}")
                return jsonify(message=f"帳號刪除失敗: {str(e)}"), 500
        else:
            logger.warning(f"用戶 {current_account} 帳號刪除失敗：帳號不存在")
            return jsonify(message="找不到要刪除的帳號"), 404
    except Exception as e:
        logger.error(f"處理帳號刪除請求時發生錯誤: {str(e)}")
        return jsonify(message=f"帳號刪除失敗: {str(e)}"), 500


def is_valid_account(account):
    """
    驗證帳號是否合法。

    帳號應僅包含字母、數字、下劃線、點號和連字符。

    Parameters:
    - account (str): 要驗證的用戶名。

    Returns:
    - bool: 如果用戶名合法，返回 True；否則返回 False。
    """
    return re.match(r"^[a-zA-Z0-9_.-]+$", account)


def is_strong_password(password):
    """
    檢查密碼是否符合規範。

    密碼至少應包含8個字符，並且必須包含字母和數字。

    Parameters:
    - password (str): 要檢查的密碼。

    Returns:
    - bool: 如果密碼符合要求，返回 True；否則返回 False。
    """
    return (
        len(password) >= 8
        and re.search(r"[A-Za-z]", password)
        and re.search(r"[0-9]", password)
    )
