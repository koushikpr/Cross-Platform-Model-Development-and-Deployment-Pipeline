import os
import json
import subprocess
from flask import Flask, render_template, request, jsonify, redirect
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)

# File to store Terraform variables
TERRAFORM_VARS_FILE = "terraform_vars.json"

# Swagger UI setup
SWAGGER_URL = '/swagger'  # Swagger UI route
API_URL = '/swagger/static/swagger.yaml'  # Path to Swagger YAML
swagger_ui_blueprint = get_swaggerui_blueprint(SWAGGER_URL, API_URL)



@app.route("/")
def home():
    return render_template("index.html")

# Load stored Terraform variables
def load_variables():
    if os.path.exists(TERRAFORM_VARS_FILE):
        with open(TERRAFORM_VARS_FILE, "r") as file:
            return json.load(file)
    return {}

# Save Terraform variables
def save_variables(data):
    with open(TERRAFORM_VARS_FILE, "w") as file:
        json.dump(data, file, indent=4)

@app.route("/terraform", methods=["POST"])
def create_instance():
    try:
        data = request.json  # Get JSON from request
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        save_variables(data)

        # Convert JSON variables to Terraform format
        tf_vars = "\n".join([f'{key} = "{value}"' for key, value in data.items()])
        with open("terraform.tfvars", "w") as tf_file:
            tf_file.write(tf_vars)

        # Run Terraform
        subprocess.run(["terraform", "init"], check=True)
        subprocess.run(["terraform", "apply", "-auto-approve"], check=True)

        # Extract relevant details from Terraform output
        output = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
        tf_output = json.loads(output.stdout)

        public_ip = tf_output.get("instance_public_ip", {}).get("value", "")
        vpc_id = tf_output.get("vpc_id", {}).get("value", "")
        subnet_id = tf_output.get("subnet_id", {}).get("value", "")

        return jsonify({
            "message": "Instance launched",
            "public_ip": public_ip,
            "vpc_id": vpc_id,
            "subnet_id": subnet_id
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/terraform/status", methods=["GET"])
def get_instance_status():
    if not os.path.exists("terraform.tfstate"):
        return jsonify({"status": "No instance deployed yet"}), 404

    # Get Terraform output details
    output = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
    tf_output = json.loads(output.stdout)

    public_ip = tf_output.get("instance_public_ip", {}).get("value", "")
    vpc_id = tf_output.get("vpc_id", {}).get("value", "")
    subnet_id = tf_output.get("subnet_id", {}).get("value", "")

    if public_ip:
        return jsonify({
            "public_ip": public_ip,
            "vpc_id": vpc_id,
            "subnet_id": subnet_id
        })
    else:
        return jsonify({"status": "Instance launching..."}), 202

@app.route("/launch", methods=["GET"])
def launch_instance():
    response = get_instance_status()
    data = response.json
    if "public_ip" in data:
        return redirect(f"http://{data['public_ip']}:8080")
    return jsonify({"message": "Instance not ready yet"}), 404



if __name__ == "__main__":
    app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)
    app.run(debug=True)
