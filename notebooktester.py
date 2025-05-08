import os
import nbformat
from flask import jsonify, request
import requests
import shutil
import subprocess

def test_local_model(request):
    try:
        if 'notebook_file' not in request.files:
            return jsonify({"error": "No file provided"}), 400

        file = request.files['notebook_file']
        model_name = request.form.get('model_name')

        if not file.filename.endswith(".ipynb"):
            return jsonify({"error": "Invalid file format. Only .ipynb allowed"}), 400

        file_path = os.path.join("/home/aman/Downloads/", file.filename)
        file.save(file_path)

        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)

        filename = f"http://10.156.115.33:8080/notebooks/Downloads/{file.filename}"

        return jsonify({
            "message": "File Uploaded to Server",
            "executed_notebook": filename
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

MODEL_BASE_DIR = "/home/aman/Downloads/models/"
JUPYTER_URL_PREFIX = "http://10.156.115.33:8080/notebooks/models/"

def upload_model(request):
    try:
        model_name = request.form.get("model_name")
        model_description = request.form.get("model_description")
        model_version = request.form.get("model_version", "1.0.0")

        file = request.files.get("model_file")
        if not model_name or not model_description or not file:
            return jsonify({"error": "Missing required fields"}), 400

        if not file.filename.endswith(".ipynb"):
            return jsonify({"error": "Invalid file format. Only .ipynb allowed"}), 400

        # Create model-specific directory
        model_dir = os.path.join(MODEL_BASE_DIR, model_name)
        os.makedirs(model_dir, exist_ok=True)

        file_path = os.path.join(model_dir, file.filename)
        file.save(file_path)

        # Optional: Verify it's a valid notebook
        with open(file_path) as f:
            nb = nbformat.read(f, as_version=4)

        notebook_url = f"{JUPYTER_URL_PREFIX}{model_name}/{file.filename}"

        return jsonify({
            "status": "Model uploaded successfully",
            "model_name": model_name,
            "version": model_version,
            "notebook_url": notebook_url
        }), 200

    except Exception as e:
        return jsonify({
            "status": "Failed to Upload",
            "model_name": model_name,
            "version": model_version,
            "notebook_url": notebook_url
        }), 404


def deployment_status(request):
    try:
        model_name = request.args.get("model_name")
        environment = request.args.get("environment", "Development")

        if not model_name:
            return jsonify({"error": "Missing model_name"}), 400

        model_dir = os.path.join(MODEL_BASE_DIR, model_name)
        if not os.path.exists(model_dir):
            return jsonify({
            "model_name": model_name,
            "status": "Model Not Found",
            "environment": environment,
            "version": "1.0.0"
        }), 404

        files = [f for f in os.listdir(model_dir) if f.endswith(".ipynb")]
        if not files:
            
            return jsonify({
            "model_name": model_name,
            "status": "No notebook found for model",
            "environment": environment,
            "version": "1.0.0"
        }), 404

        notebook_file = files[0]
        notebook_url = f"{JUPYTER_URL_PREFIX}{model_name}/{notebook_file}"

        try:
            res = requests.get(notebook_url)
            status = "Deployed" if res.status_code == 200 else "Not Available"
        except Exception:
            status = "Not Available"

        return jsonify({
            "model_name": model_name,
            "status": status,
            "environment": environment,
            "version": "1.0.0"
        }), 200

    except Exception as e:
        return jsonify({
            "model_name": model_name,
            "status": status,
            "environment": environment,
            "version": "1.0.0"
        }), 404

DEPLOY_SCRIPT = "deployment/generate_pred_script.py"
DEPLOY_BASE = "/home/aman/Downloads/deployed_models/"
APP_PORT = 5001

def deploy_model_as_api(request):
    try:
        model_name = request.args.get("model_name")
        model_filename = request.args.get("model_filename")  # e.g., Test.ipynb
        model_class = request.args.get("model_code_name")
        environment = request.args.get("environment", "Production")

        if not all([model_name, model_filename, model_class]):
            return jsonify({"error": "Missing required fields"}), 400

        # Prepare paths
        model_dir = os.path.join(MODEL_BASE_DIR, model_name)
        if not os.path.exists(model_dir):
            return jsonify({"error": "Model not found"}), 404

        deploy_dir = os.path.join(DEPLOY_BASE, model_name)
        os.makedirs(deploy_dir, exist_ok=True)

        # Step 1: Copy .ipynb and model.pt
        for fname in [model_filename, "model.pt"]:
            src = os.path.join(model_dir, fname)
            dst = os.path.join(deploy_dir, fname)
            if not os.path.exists(src):
                return jsonify({"error": f"File not found: {fname}"}), 404
            shutil.copy(src, dst)

        # Step 2: Copy deployment files
        for file in os.listdir("deployment"):
            full_path = os.path.join("deployment", file)
            if os.path.isfile(full_path):
                shutil.copy(full_path, deploy_dir)

        # Step 3: Run generate_pred_script.py
        gen_cmd = [
            "python3", "generate_pred_script.py",
            model_filename, model_class
        ]
        subprocess.run(gen_cmd, cwd=deploy_dir, check=True)

        # Step 4: Run app.py on port 5001
        subprocess.Popen(
            ["python3", "app.py"],
            cwd=deploy_dir,
            stdout=open(os.path.join(deploy_dir, "app_stdout.log"), "w"),
            stderr=open(os.path.join(deploy_dir, "app_stderr.log"), "w"),
            start_new_session=True  # important for detaching the process cleanly
        )

        # Step 5: Return endpoint
        return jsonify({
            "status": "Deployment started",
            "url": f"http://localhost:{APP_PORT}/predict"
        }), 200

    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Script failed: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500