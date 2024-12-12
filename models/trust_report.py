from extensions import db


class TrustReport(db.Model):
    __tablename__ = "trust_report"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    filename = db.Column(db.String(50), nullable=False)

    def __init__(self, user_id, filename):
        self.user_id = user_id
        self.filename = filename
