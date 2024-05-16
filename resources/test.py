from flask.views import MethodView
from flask_smorest import Blueprint, abort

from db import db

blp = Blueprint("Tests", "tests", description="testing")


@blp.route("/test")
class UserList(MethodView):
    @blp.response(200)
    def get(self):
        return {"Hello": 123}
