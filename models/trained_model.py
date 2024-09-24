from sqlalchemy import DateTime
from extensions import db
import uuid


class TrainedModel(db.Model):
    __tablename__ = "trained_model"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    modelname: str = db.Column(db.String(50), nullable=False)
    start_time = db.Column(DateTime(timezone=True))
    end_time = db.Column(DateTime(timezone=True))

    def __init__(self, user_id, start_time, end_time):
        self.user_id = user_id
        self.modelname = str(uuid.uuid4())
        self.start_time = start_time
        self.end_time = end_time
