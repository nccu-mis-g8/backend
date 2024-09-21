from extensions import db
import uuid


class TrainedModel(db.Model):
    __tablename__ = "trained_model"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    modelname: str = db.Column(db.String(36), nullable=False)
    is_trained: bool = db.Column(db.Boolean, default=False, nullable=False)

    def __init__(self, user_id):
        self.user_id = user_id
        self.modelname = str(uuid.uuid4())
        self.is_trained = False
