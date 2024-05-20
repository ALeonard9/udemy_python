import os
import redis
from flask.views import MethodView
from flask_smorest import Blueprint, abort
from flask_jwt_extended import jwt_required, get_jwt
from passlib.hash import pbkdf2_sha256
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    jwt_required,
    create_refresh_token,
    get_jwt_identity,
)

from rq import Queue

from tasks import send_user_registration_email

from blocklist import BLOCKLIST

from db import db
from models import UserModel
from schemas import UserSchema, UserRegisterSchema
from tasks import send_user_registration_email
from sqlalchemy import or_

connection = redis.from_url(
    os.getenv(
        "REDIS_URL",
    ),
)  # Get this from Render.com or run in Docker
try:
    connection.ping()
    queue = Queue("emails", connection=connection, default_timeout=3600)
except Exception as e:
    print(f"Error: {e}")

blp = Blueprint("Users", "users", description="Operations on users")


@jwt_required()
@blp.route("/user")
class UserList(MethodView):
    @blp.response(200, UserSchema(many=True))
    def get(self):
        users = UserModel.query.all()
        return users


@blp.route("/register")
class UserRegister(MethodView):
    @blp.arguments(UserRegisterSchema)
    def post(self, user_data):
        if UserModel.query.filter(
            or_(
                UserModel.username == user_data["username"],
                UserModel.email == user_data["email"],
            )
        ).first():
            abort(409, message="A user with that username or email already exists.")

        user = UserModel(
            username=user_data["username"],
            email=user_data["email"],
            password=pbkdf2_sha256.hash(user_data["password"]),
        )
        db.session.add(user)
        db.session.commit()

        try:
            queue.enqueue(send_user_registration_email, user.email, user.username)
        except Exception as e:
            print(f"Error: {e}")
            abort(500, message="Could not send to queue")

        return {"message": "User created successfully."}, 201


@blp.route("/logout")
class UserLogout(MethodView):
    @jwt_required()
    @blp.response(200)
    def post(self):
        jti = get_jwt()["jti"]
        BLOCKLIST.add(jti)
        return {"message": "Successfully logged out"}, 200


@blp.route("/user/<int:user_id>")
class User(MethodView):
    @jwt_required()
    @blp.response(200, UserSchema)
    def get(self, user_id):
        user = UserModel.query.get_or_404(user_id)
        return user

    @jwt_required()
    def delete(self, user_id):
        jwt = get_jwt()
        if not jwt["is_admin"]:
            abort(401, message="Admin privilege required")
        user = UserModel.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return {"message": "User deleted"}, 200


@blp.route("/login")
class UserLogin(MethodView):
    @blp.arguments(UserSchema)
    def post(self, user_data):
        try:
            user = UserModel.query.filter(
                UserModel.username == user_data["username"]
            ).first()
            if user and pbkdf2_sha256.verify(user_data["password"], user.password):
                access_token = create_access_token(identity=user.id, fresh=True)
                refresh_token = create_refresh_token(identity=user.id)
                return {
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                }, 200

            abort(401, message="Invalid credentials")
        except Exception as e:
            print(f"Error: {e}")
            abort(500, message="Could not log in user")


@blp.route("/refresh")
class UserRefresh(MethodView):
    # Refresh=True means that the token is a refresh token
    @jwt_required(refresh=True)
    def post(self):
        current_user = get_jwt_identity()
        new_token = create_access_token(identity=current_user, fresh=False)
        return {"access_token": new_token}, 200
