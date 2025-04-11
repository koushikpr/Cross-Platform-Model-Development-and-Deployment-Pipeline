import os
import json
import subprocess
from flask import jsonify

TERRAFORM_VARS_FILE_EC2 = "terraform/ec2/variables.tfvars"

def save_variables(data, path):
    with open(path, "w") as file:
        json.dump(data, file, indent=4)

def create_instance_ec2(request):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        save_variables(data, TERRAFORM_VARS_FILE_EC2)
        tf_vars = "\n".join([f'{key} = "{value}"' for key, value in data.items()])
        with open("terraform/ec2/gpuinstancelaunch-ec2.tfvars", "w") as tf_file:
            tf_file.write(tf_vars)

        subprocess.run(["terraform", "init", "-chdir=terraform/ec2"], check=True)
        subprocess.run(["terraform", "apply", "-auto-approve", "-chdir=terraform/ec2"], check=True)

        output = subprocess.run(["terraform", "output", "-json", "-chdir=terraform/ec2"], capture_output=True, text=True)
        tf_output = json.loads(output.stdout)

        return jsonify({
            "message": "EC2 Instance launched",
            "public_ip": tf_output.get("instance_public_ip", {}).get("value", ""),
            "vpc_id": tf_output.get("vpc_id", {}).get("value", ""),
            "subnet_id": tf_output.get("subnet_id", {}).get("value", "")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
