import os
import json
import subprocess
from flask import Flask, render_template, request, jsonify, redirect

app = Flask(__name__)

# File to store Terraform variables
TERRAFORM_VARS_FILE = "terraform_vars.json"

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

        # Extract public IP from Terraform output
        output = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
        tf_output = json.loads(output.stdout)
        public_ip = tf_output.get("instance_public_ip", {}).get("value", "")

        return jsonify({"message": "Instance launched", "public_ip": public_ip}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/terraform/status", methods=["GET"])
def get_instance_status():
    if not os.path.exists("terraform.tfstate"):
        return jsonify({"status": "No instance deployed yet"}), 404

    # Get the public IP from Terraform
    output = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
    tf_output = json.loads(output.stdout)
    public_ip = tf_output.get("instance_public_ip", {}).get("value", "")

    if public_ip:
        return jsonify({"public_ip": public_ip})
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
    app.run(debug=True)
