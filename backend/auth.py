import os
import datetime
from functools import wraps

import jwt
from dotenv import load_dotenv
from flask import g, jsonify, request

load_dotenv()
SECRET = os.environ["SECRET_KEY"]


def make_token(user_id):
    # "sub" (subject) = who this token is for; "exp" = expiration time (7 days from now)
    payload = {
        "sub": str(user_id),
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7),
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")  # encodes the payload into a JWT token using the secret key and HS256 algorithm


def login_required(f):
    """Put @login_required under a route to make it need a valid token.
    Inside the route, g.user_id is the logged-in user's id."""
    @wraps(f) #keep the original functions name
    def wrapper(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            return jsonify(error="login required"), 401
        try:
            payload = jwt.decode(header[7:], SECRET, algorithms=["HS256"])
        except jwt.InvalidTokenError:
            return jsonify(error="invalid or expired token"), 401
        g.user_id = int(payload["sub"])
        return f(*args, **kwargs)

    return wrapper