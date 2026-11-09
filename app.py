from flask import Flask
import socket
import redis
import os


app = Flask(__name__)
redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_host = os.getenv("REDIS_HOST","redis")
redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True
)

@app.route("/", methods=["GET"])
def home():
    hostname = socket.gethostname()
    return {"message": "Hello DevOps" , "host": hostname }

@app.route("/visits", methods=["GET"])
def count():
    num = redis_client.incr("visits")
    return {"visits": num }


