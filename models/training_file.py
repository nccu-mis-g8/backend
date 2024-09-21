from extensions import db
import uuid


class TrainingFile(db.Model):
    __tablename__ = "training_file"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String(36), nullable=False)
    is_trained: bool = db.Column(db.Boolean, default=False, nullable=False)

    # 上傳file後先生成TrainingFile物件，再從TrainingFile object拿filename做為檔名存file。
    def __init__(self, user_id):
        self.user_id = user_id
        self.filename = str(uuid.uuid4()) + ".csv"
        self.is_trained = False
