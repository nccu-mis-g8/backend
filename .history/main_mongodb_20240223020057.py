from flask import *
import pymongo


app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)

app.secret_key="nccumisg8"








app.run()