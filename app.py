import os
import json
import subprocess
from flask import Flask, render_template, request, jsonify, redirect
from flask_swagger_ui import get_swaggerui_blueprint
import paramiko
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor


app = Flask(__name__)

# File to store Terraform variables
TERRAFORM_VARS_FILE_EC2 = "terraform/ec2/variables.tfvars"
TERRAFORM_VARS_FILE_OPENSTACK = "terraform/openstack/variables.tfvars"


SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'  # Path to your Swagger JSON definition
swagger_ui_bp = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Flask Terraform API"})
app.register_blueprint(swagger_ui_bp, url_prefix=SWAGGER_URL)


@app.route("/")
def home():
    return render_template("index.html")

# Load stored Terraform variables for EC2 and OpenStack
def load_variables(path):
    if os.path.exists(path):
        with open(path, "r") as file:
            return json.load(file)
    return {}

# Save Terraform variables for EC2 and OpenStack
def save_variables(data, path):
    with open(path, "w") as file:
        json.dump(data, file, indent=4)

# EC2 Launch Endpoint
@app.route("/terraform/ec2", methods=["POST"])
def create_instance_ec2():
    try:
        data = request.json  # Get JSON from request
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        save_variables(data, TERRAFORM_VARS_FILE_EC2)

        # Convert JSON variables to Terraform format for EC2
        tf_vars = "\n".join([f'{key} = "{value}"' for key, value in data.items()])
        with open("terraform/ec2/gpuinstancelaunch-ec2.tfvars", "w") as tf_file:
            tf_file.write(tf_vars)

        # Run Terraform for EC2
        subprocess.run(["terraform", "init", "-chdir=terraform/ec2"], check=True)
        subprocess.run(["terraform", "apply", "-auto-approve", "-chdir=terraform/ec2"], check=True)

        # Extract relevant details from Terraform output for EC2
        output = subprocess.run(["terraform", "output", "-json", "-chdir=terraform/ec2"], capture_output=True, text=True)
        tf_output = json.loads(output.stdout)   

        public_ip = tf_output.get("instance_public_ip", {}).get("value", "")
        vpc_id = tf_output.get("vpc_id", {}).get("value", "")
        subnet_id = tf_output.get("subnet_id", {}).get("value", "")

        return jsonify({
            "message": "EC2 Instance launched",
            "public_ip": public_ip,
            "vpc_id": vpc_id,
            "subnet_id": subnet_id
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# OpenStack Launch Endpoint
@app.route("/terraform/openstack", methods=["POST"])
def create_instance_openstack():
    try:
        data = request.json  # Get JSON from request
        if not data:
            return jsonify({"error": "Invalid JSON data"}), 400

        save_variables(data, TERRAFORM_VARS_FILE_OPENSTACK)

        # Convert JSON variables to Terraform format for OpenStack
        tf_vars = "\n".join([f'{key} = "{value}"' for key, value in data.items()])
        with open("terraform/openstack/gpuinstancelaunch-openstack.tfvars", "w") as tf_file:
            tf_file.write(tf_vars)

        # Run Terraform for OpenStack
        subprocess.run(["terraform", "init", "-chdir=terraform/openstack"], check=True)
        subprocess.run(["terraform", "apply", "-auto-approve", "-chdir=terraform/openstack"], check=True)

        # Extract relevant details from Terraform output for OpenStack
        output = subprocess.run(["terraform", "output", "-json", "-chdir=terraform/openstack"], capture_output=True, text=True)
        tf_output = json.loads(output.stdout)

        public_ip = tf_output.get("instance_public_ip", {}).get("value", "")
        vpc_id = tf_output.get("vpc_id", {}).get("value", "")
        subnet_id = tf_output.get("subnet_id", {}).get("value", "")

        return jsonify({
            "message": "OpenStack Instance launched",
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

    # Get Terraform output details for EC2 or OpenStack
    output = subprocess.run(["terraform", "output", "-json"], capture_output=True, text=True)
    tf_output = json.loads(output.stdout)

    public_ip = tf_output.get("instance_public_ip", {}).get("value", "")




FEDORA_PLAYBOOKS_DIR = "/home/aman/Desktop/Cross-Platform-Model-Development-and-Deployment-Pipeline/ansible/configurations/"
LIBRARY_PLAYBOOKS_DIR = "/home/aman/Desktop/Cross-Platform-Model-Development-and-Deployment-Pipeline/ansible/library/"

@app.route("/deploy/fedora", methods=["POST"])
def deploy_fedora():
    try:
        data = request.json
        server_ip = data.get("server_ip")
        ssh_user = data.get("ssh_user")
        ssh_password = data.get("ssh_password")
        selected_libraries = data.get("libraries", [])


        print(server_ip,ssh_user,ssh_password)
        if not server_ip or not ssh_user or not ssh_password:
            return jsonify({"error": "Missing required SSH details"}), 400

        # Establish SSH Connection
        print("Connecting to SSH Client: "+ssh_user+"@"+server_ip)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        

        try:
            ssh.connect(server_ip, username=ssh_user, password=ssh_password)
            print("Connected to "+ssh_user+"@"+server_ip)
        except Exception as e:
            return jsonify({"error": f"SSH Connection failed: {str(e)}"}), 500

        ssh.exec_command("sudo su")
        # Install Ansible if not installed
        print("Verifying Ansible Installed")
        stdin, stdout, stderr = ssh.exec_command("which ansible || dnf install -y ansible")
        stdout.channel.recv_exit_status()

        # Run Base Configuration Playbook
        nvidia = f"{FEDORA_PLAYBOOKS_DIR}nvidia-setup.yml"
        jupyter = f"{FEDORA_PLAYBOOKS_DIR}jupyter-setup.yml"
        grafana = f"{FEDORA_PLAYBOOKS_DIR}grafana-setup.yml"
        print("Installing NVIDIA CUDA Toolkit")
        print("Installing Grafana")
        print("Installing Jupyter NoteBook")
        ssh.exec_command(f"ansible-playbook {jupyter}")

        # Run selected library playbooks
        for lib in selected_libraries:
            print("Installing Library: " + lib)
            lib_playbook = f"{LIBRARY_PLAYBOOKS_DIR}{lib}.yml"
            ssh.exec_command(f"ansible-playbook {lib_playbook}")

        ssh.close()

        return jsonify({"message": "Fedora Server setup complete"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test/local", methods=["POST"])
def test_local_model():
    try:
        if 'notebook_file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['notebook_file']
        model_name = request.form.get('model_name')

        if not file.filename.endswith(".ipynb"):
            return jsonify({"error": "Invalid file format. Only .ipynb allowed"}), 400

        file_path = os.path.join("/home/aman/Downloads/", file.filename)
        file.save(file_path)

        # Execute the Jupyter Notebook
        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)

        return redirect('https://10.156.115.33:8080/Downloads/'+file.filename)

        

        # Save the executed notebook
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500







if __name__ == "__main__":

    app.run(debug=True)