from flask.views import MethodView
from flask_smorest import Blueprint, abort
import requests

import os
import redis
from rq import Queue

blp = Blueprint("Tests", "tests", description="testing")


def count_words_at_url(url):
    resp = requests.get(url)
    return len(resp.text.split())


@blp.route("/test")
class UserList(MethodView):
    @blp.response(200)
    def post(self):
        connection = redis.from_url(
            os.getenv(
                "REDIS_URL",
            ),
            ssl_cert_reqs=None,  # This disables certificate verification
            ssl_ca_certs=None,
        )  # Get this from Render.com or run in Docker
        try:
            connection.ping()
            q = Queue("tests", connection=connection, default_timeout=3600)
            result = q.enqueue(count_words_at_url, "http://nvie.com")

        except Exception as e:
            print(f"Error: {e}")
        return "OK"
