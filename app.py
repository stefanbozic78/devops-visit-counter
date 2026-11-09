from flask import Flask,request
import socket
import redis
import os


app = Flask(__name__)
app_port = int(os.getenv("APP_PORT", "8080"))

redis_port = int(os.getenv("REDIS_PORT", "6379"))
redis_host = os.getenv("REDIS_HOST","redis")



redis_client = redis.Redis(
    host=redis_host,
    port=redis_port,
    decode_responses=True
)

# log
@app.before_request
def log_request():
    print(f"Request: {request.method} {request.path}", flush=True)



@app.route("/", methods=["GET"])
def home():
    hostname = socket.gethostname()
    return {"message": "Hello DevOps" , "host": hostname }

@app.route("/visits", methods=["GET"])
def count():
    num = redis_client.incr("visits")
    return {"visits": num }


@app.route("/health", methods=["GET"])
def health():
    try:
        redis_client.ping()
        return {"status": "ok"},200
    except redis.exceptions.RedisError:
        return {"status": "error"},503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app_port)

    

