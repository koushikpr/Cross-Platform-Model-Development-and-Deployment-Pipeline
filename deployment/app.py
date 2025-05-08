from flask import Flask, request, jsonify
from pred import predict

app = Flask(__name__)

@app.route("/predict", methods=["POST"])
def predict_route():
    if "file" not in request.files:
        return jsonify({"error": "Missing file"}), 400
    try:
        image_file = request.files["file"]
        result = predict(image_file)
        return jsonify({"prediction": result}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
