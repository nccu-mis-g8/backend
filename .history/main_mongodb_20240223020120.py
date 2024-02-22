from flask import *
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)

app.secret_key="nccumisg8"








app.run()