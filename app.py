import os
import json
import subprocess
from flask import Flask, render_template, request, jsonify, redirect
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
import paramiko
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
from prometheus_client import Counter, Summary, Gauge, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
import joblib
from pathlib import Path

# Define Prometheus metrics
INFERENCE_REQUESTS = Counter('inference_requests_total', 'Total number of inference requests')
INFERENCE_LATENCY = Summary('inference_latency_seconds', 'Time spent handling inference')
MODEL_LOADED = Gauge('model_loaded', 'Number of models currently loaded', ['model_name'])
MODEL_PREDICTIONS = Counter('model_predictions_total', 'Total number of predictions per model', ['model_name'])
MODEL_LATENCY = Summary('model_latency_seconds', 'Time spent handling predictions per model', ['model_name'])

# Create models directory if it doesn't exist
MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True, mode=0o777)

app = Flask(__name__)

# Configure CORS to allow requests from all origins
CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})

# Store loaded models in memory
loaded_models = {}

# Load existing models on startup
def load_existing_models():
    print("Loading existing models...")
    for model_file in MODELS_DIR.glob("*.joblib"):
        try:
            model_name = model_file.stem  # Get filename without extension
            print(f"Loading model: {model_name}")
            model = joblib.load(str(model_file))
            loaded_models[model_name] = model
            print(f"Model loaded successfully: {model_name}")
        except Exception as e:
            print(f"Error loading model {model_file}: {str(e)}")

# Load existing models
load_existing_models()
print(f"Available models: {list(loaded_models.keys())}")

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

        filename = "http://10.156.115.33:8080/notebooks/Downloads/"+file.filename

        res = {
            "message": "File Uploaded to Server",
            "executed_notebook": filename
        }

        return jsonify(res), 200

        

        

        # Save the executed notebook
       
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/upload-model', methods=['POST'])
def upload_model():
    try:
        print("Received upload-model request")
        if 'file' not in request.files:
            print("No file in request.files")
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        print(f"Received file: {file.filename}")
        if file.filename == '':
            print("Empty filename")
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.endswith('.joblib'):
            print(f"Invalid file extension: {file.filename}")
            return jsonify({'error': 'Only .joblib files are supported'}), 400
        
        # Save the model file
        model_path = MODELS_DIR / file.filename
        print(f"Saving model to: {model_path}")
        file.save(str(model_path))
        
        # Load the model into memory
        print(f"Loading model from: {model_path}")
        model = joblib.load(str(model_path))
        model_name = file.filename.replace('.joblib', '')  # Store without extension
        loaded_models[model_name] = model
        MODEL_LOADED.labels(model_name=model_name).set(1)  # Set model as loaded
        print(f"Model loaded successfully. Available models: {list(loaded_models.keys())}")
        
        return jsonify({
            'message': 'Model uploaded successfully',
            'model_name': model_name
        })
    except Exception as e:
        print(f"Error in upload-model: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/predict', methods=['POST'])
@INFERENCE_LATENCY.time()
def predict():
    try:
        INFERENCE_REQUESTS.inc()
        
        data = request.json
        print(f"Received prediction request: {data}")
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get the model name from the request
        model_name = data.get('model_name')
        print(f"Requested model: {model_name}")
        print(f"Available models: {list(loaded_models.keys())}")
        
        if not model_name:
            return jsonify({'error': 'Model name is required'}), 400
            
        if model_name not in loaded_models:
            return jsonify({'error': f'Model not found: {model_name}'}), 404
        
        model = loaded_models[model_name]
        
        # Prepare features for prediction
        features = [
            data.get('sepal_length'),
            data.get('sepal_width'),
            data.get('petal_length'),
            data.get('petal_width')
        ]
        
        if any(f is None for f in features):
            return jsonify({'error': 'Missing required features'}), 400
        
        # Make prediction with timing
        with MODEL_LATENCY.labels(model_name=model_name).time():
            prediction = model.predict([features])[0]
            MODEL_PREDICTIONS.labels(model_name=model_name).inc()
        
        return jsonify({
            'prediction': int(prediction),
            'model_used': model_name
        })
    except Exception as e:
        print(f"Error in predict endpoint: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/metrics')
def metrics():
    # Update model loaded metrics
    for model_name in loaded_models:
        MODEL_LOADED.labels(model_name=model_name).set(1)
    
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

if __name__ == "__main__":

    app.run(debug=True)