import time
import random
import string
import base64
import requests
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

API_KEY = "sk_39c982b121d4c998671f928d0d26c297199dda82495ec88e37a51bbafe92b663"
API_URL = "https://api.nexusify.co/v1/generate-image"

image_cache = {}


def generate_id():
    rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{int(time.time() * 1000)}-{rand}"


@app.route("/api/image")
def generate_image():
    start_time = time.time()
    prompt = request.args.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "Missing 'prompt' query parameter"}), 400

    try:
        api_response = requests.post(
            API_URL,
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "prompt": prompt,
                "model": "flux",
                "width": 1024,
                "height": 1024
            },
            timeout=60
        )
        api_response.raise_for_status()
        data = api_response.json()

        image_url = data.get("imageUrl")
        if not image_url:
            return jsonify({"error": "No imageUrl in response", "response": data}), 500

        if image_url.startswith("/"):
            image_url = "https://api.nexusify.co" + image_url

        img_response = requests.get(image_url, timeout=60)
        img_response.raise_for_status()

        image_data = base64.b64encode(img_response.content).decode("utf-8")

        image_id = generate_id()
        image_cache[image_id] = image_data

        duration = f"{time.time() - start_time:.2f}s"
        host_url = request.host_url.rstrip("/")
        served_url = f"{host_url}/generated/{image_id}.png"

        return jsonify({
            "message": "Image generated successfully",
            "status": "success",
            "image": served_url,
            "imageId": image_id,
            "prompt": prompt,
            "duration": duration
        })

    except requests.exceptions.HTTPError as e:
        duration = f"{time.time() - start_time:.2f}s"
        return jsonify({"error": str(e), "duration": duration}), 500
    except Exception as e:
        duration = f"{time.time() - start_time:.2f}s"
        return jsonify({"error": str(e), "duration": duration}), 500


@app.route("/generated/<image_id>.png")
def serve_image(image_id):
    image_data = image_cache.get(image_id)

    if not image_data:
        return jsonify({"error": "Image not found"}), 404

    image_bytes = base64.b64decode(image_data)

    return Response(
        image_bytes,
        mimetype="image/png",
        headers={"Content-Length": len(image_bytes)}
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
