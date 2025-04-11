import os
import json
import subprocess
from flask import jsonify

TERRAFORM_VARS_FILE_OPENSTACK = "terraform/openstack/variables.tfvars"

def save_variables(data, path):
    with open(path, "w") as file:
        json.dump(data, file, indent=4)

def create_instance_openstack(request):
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        save_variables(data, TERRAFORM_VARS_FILE_OPENSTACK)
        tf_vars = "\n".join([f'{key} = "{value}"' for key, value in data.items()])
        with open("terraform/openstack/gpuinstancelaunch-openstack.tfvars", "w") as tf_file:
            tf_file.write(tf_vars)

        subprocess.run(["terraform", "init", "-chdir=terraform/openstack"], check=True)
        subprocess.run(["terraform", "apply", "-auto-approve", "-chdir=terraform/openstack"], check=True)

        output = subprocess.run(["terraform", "output", "-json", "-chdir=terraform/openstack"], capture_output=True, text=True)
        tf_output = json.loads(output.stdout)

        return jsonify({
            "message": "OpenStack Instance launched",
            "public_ip": tf_output.get("instance_public_ip", {}).get("value", ""),
            "vpc_id": tf_output.get("vpc_id", {}).get("value", ""),
            "subnet_id": tf_output.get("subnet_id", {}).get("value", "")
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
