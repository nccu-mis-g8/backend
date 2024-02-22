from flask import Flask
from flask import request
import json
from flask import redirect
from flask import render_template
from flask import session
import pymongo

app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/"
)

app.secret_key="nccumisg8"








app.run()