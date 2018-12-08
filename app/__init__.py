from flask import Flask


flask_app = Flask("__engine_dashboard__")


from .views import *