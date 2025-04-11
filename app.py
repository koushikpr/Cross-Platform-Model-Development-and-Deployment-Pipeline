from flask import Flask, render_template, request
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


from cloudsetup import create_instance_ec2
from openstacksetup import create_instance_openstack
from fedorasetup import deploy_fedora
from notebooktester import test_local_model, upload_model, deployment_status
from s3modelmanager import upload_model_to_s3, get_model_status_s3
app = Flask(__name__)

SWAGGER_URL = '/swagger'
API_URL = '/static/swagger.json'
swagger_ui_bp = get_swaggerui_blueprint(SWAGGER_URL, API_URL, config={'app_name': "Flask Terraform API"})
app.register_blueprint(swagger_ui_bp, url_prefix=SWAGGER_URL)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/terraform/ec2", methods=["POST"])
def launch_ec2():
    return create_instance_ec2(request)

@app.route("/terraform/openstack", methods=["POST"])
def launch_openstack():
    return create_instance_openstack(request)

@app.route("/deploy/fedora", methods=["POST"])
def setup_fedora():
    return deploy_fedora(request)

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
def test_model():
    return test_local_model(request)

@app.route("/model/upload", methods=["POST"])
def upload_model_route():
    return upload_model(request)

@app.route("/model/status", methods=["GET"])
def check_model_status():
    return deployment_status(request)


@app.route("/model/upload/s3", methods=["POST"])
def upload_model_s3():
    return upload_model_to_s3(request)

@app.route("/model/status/s3", methods=["GET"])
def check_model_s3():
    return get_model_status_s3(request)

if __name__ == "__main__":
    app.run(debug=True)


