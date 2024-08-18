from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(255), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)
        
    def check_password(self, password):
        """
        驗證輸入的密碼是否與存儲的哈希密碼相符。

        Parameters:
        - password (str): 用戶輸入的明文密碼。

        Returns:
        - bool: 如果密碼相符，返回 True，否則返回 False。
        """
        return check_password_hash(self.password, password)
    
    @classmethod
    def get_user_by_username(cls, username):
        """
        根據用戶名查找並返回對應的 User 實例。

        Parameters:
        - username (str): 要查找的用戶名。

        Returns:
        - User 實例，如果找到；否則返回 None。
        """
        return cls.query.filter_by(username=username).first()
    
    def save(self):
        """
        將當前 User 實例保存到資料庫中。
        """
        db.session.add(self)
        db.session.commit()

    def delete(self):
        """
        從資料庫中刪除當前 User 實例。
        """
        db.session.delete(self)
        db.session.commit()


class RefreshToken(db.Model):
    __tablename__ = 'refreshTokens'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token = db.Column(db.Text, nullable=False)
    revoked = db.Column(db.Boolean, default=False)

    def save(self):
        """
        將當前 RefreshToken 實例保存到資料庫中。
        """
        db.session.add(self)
        db.session.commit()

    def revoke(self):
        """
        撤銷當前的 RefreshToken，將其設置為已撤銷狀態。
        """
        self.revoked = True
        db.session.commit()
        
    @classmethod
    def find_by_token_and_user(cls, token, user_id):
        """
        根據 token 和 user_id 查找對應的 RefreshToken 實例。

        Parameters:
        - token (str): 要查找的 Refresh Token。
        - user_id (int): 用戶的 ID。

        Returns:
        - RefreshToken 實例，如果找到；否則返回 None。
        """
        return cls.query.filter_by(token=token, user_id=user_id).first()
    
    @classmethod
    def delete_revoked_tokens(cls, user_id):
        """
        刪除指定用戶所有已撤銷的 refresh token。

        Parameters:
        - user_id (int): 用戶的 ID。

        Returns:
        - None
        """
        cls.query.filter_by(user_id=user_id, revoked=True).delete()
        db.session.commit()
        
    @classmethod
    def find_by_userId(cls, user_id):
        """
        根據用戶 ID 查找對應的 refresh token。

        Parameters:
        - user_id (int): 用戶的 ID。

        Returns:
        - RefreshToken 實例，如果找到；否則返回 None。
        """
        return cls.query.filter_by(user_id=user_id).first()