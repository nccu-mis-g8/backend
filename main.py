from flask import Flask
from extensions import db, jwt
from models import TokenBlocklist, User
from auth import auth_bp
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config.from_prefixed_env()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 

#initialize 
db.init_app(app)
jwt.init_app(app)

# register blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")

@jwt.token_in_blocklist_loader
def check_if_token_in_blacklist(jwt_header, jwt_payload):
    jti = jwt_payload['jti']
    
    token = db.session.query(TokenBlocklist).filter(TokenBlocklist.jti == jti).scalar()

    return token is not None

# define table
# @app.before_request
# def create_tables():
#     db.create_all()
    
if __name__ == '__main__':
    app.run(debug=True)

