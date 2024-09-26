from sqlalchemy import DateTime, func
from extensions import db
import uuid


class UserInfo(db.Model):
    __tablename__ = "user_info"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String(255), nullable=True)

    def __init__(self, user_id, filename=None):
        self.user_id = user_id
        self.modelname = str(uuid.uuid4())
        self.filename = filename
