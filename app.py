from flask import Flask, render_template, request
from flask_swagger_ui import get_swaggerui_blueprint
from cloudsetup import create_instance_ec2
from openstacksetup import create_instance_openstack
from fedorasetup import deploy_fedora
from notebooktester import test_local_model, upload_model, deployment_status
from s3modelmanager import upload_model_to_s3, get_model_status_s3
from flask_cors import CORS


app = Flask(__name__)



CORS(app, resources={r"/*": {"origins": "*"}})

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


