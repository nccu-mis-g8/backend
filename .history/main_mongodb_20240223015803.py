from flask import Flask
from flask import request

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)