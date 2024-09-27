from typing import List, Optional
from models.user_info import UserInfo
from extensions import db
import logging


class UserInfoRepo:
    @staticmethod
    def create_user_info(user_id, filename) -> Optional[UserInfo]:
        user_info = UserInfo(user_id=user_id, filename=filename)
        db.session.add(user_info)
        try:
            db.session.commit()
            return user_info
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating user_info for user {user_id}: {e}")
            return None

    @staticmethod
    def get_all_user_info() -> List[UserInfo]:
        return UserInfo.query.all()

    @staticmethod
    def find_user_info_by_user_id(user_id) -> Optional[UserInfo]:
        return UserInfo.query.filter_by(user_id=user_id).first()

    @staticmethod
    def delete_user_info_by_user_id(user_id):
        UserInfo.query.filter_by(user_id=user_id).delete()
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logging.error(f"Error delete user_info for user {user_id}: {e}")