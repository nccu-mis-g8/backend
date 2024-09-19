from extensions import db, jwt
from auth.auth_controller import auth_bp
from dotenv import load_dotenv
from flask_swagger_ui import get_swaggerui_blueprint
from flasgger import Swagger
from flask import Flask

# from train_model.train_model_controller import train_model_bp

load_dotenv()

app = Flask(__name__)
app.config.from_prefixed_env()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SWAGGER"] = {
    "title": "API Documentation",
    "uiversion": 3,
    "specs": [
        {
            "endpoint": "swagger",
            "route": "/swagger.json",
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/swagger/",
}

# initialize
db.init_app(app)
jwt.init_app(app)

# Initialize Swagger
swagger = Swagger(app)

SWAGGER_URL = "/apidocs"  # URL for exposing Swagger UI (without trailing '/')
API_URL = "/swagger.json"  # Our API url (can of course be a local resource)

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL, API_URL, config={"app_name": "Local Test API"}
)

# register necessary blueprint
app.register_blueprint(auth_bp, url_prefix="/auth")
# app.register_blueprint(train_model_bp, url_prefix="/finetune")

# Register Swagger UI blueprint
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

# define table
# @app.before_request
# def create_tables():
#     db.create_all()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
