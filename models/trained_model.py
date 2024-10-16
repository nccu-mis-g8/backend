from typing import Optional
from sqlalchemy import DateTime, func
from extensions import db
import uuid


class TrainedModel(db.Model):
    __tablename__ = "trained_model"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    modelname: str = db.Column(db.String(50), nullable=False)
    modelphoto: str = db.Column(db.String(255), nullable=True)
    anticipation =  db.Column(db.Text, nullable=True)
    start_time: DateTime = db.Column(DateTime(timezone=True), default=func.now())
    end_time: Optional[DateTime] = db.Column(DateTime(timezone=True), nullable=True)

    def __init__(self, user_id, end_time=None):
        self.user_id = user_id
        self.modelname = str(uuid.uuid4())
        self.end_time = end_time