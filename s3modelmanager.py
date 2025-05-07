import nbformat
import boto3
from flask import jsonify
from botocore.exceptions import ClientError
import csv
import os

S3_BUCKET_NAME = "mldaasmodels"  # Replace with your actual bucket name
S3_FOLDER = "models/"

CREDENTIALS_CSV = "s3key.csv"
def get_aws_credentials_from_csv():
    with open(CREDENTIALS_CSV, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        row = next(reader)
        return row["Access key ID"], row["Secret access key"]

aws_access_key_id, aws_secret_access_key = get_aws_credentials_from_csv()


s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
    region_name="us-east-1"  
)


def upload_model_to_s3(request):
    try:
        model_name = request.form.get("model_name")
        model_description = request.form.get("model_description")
        model_version = request.form.get("model_version", "1.0.0")
        file = request.files.get("model_file")

        if not model_name or not model_description or not file:
            return jsonify({"error": "Missing required fields"}), 400

        if not file.filename.endswith(".ipynb"):
            return jsonify({"error": "Invalid file format. Only .ipynb allowed"}), 400

        # Optional: validate notebook format
        nb = nbformat.read(file, as_version=4)
        file.seek(0)  # Reset file pointer after reading

        s3_key = f"{S3_FOLDER}{model_name}/{file.filename}"

        response = s3.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file,
            ACL='public-read',
            Metadata={
                "model_name": model_name,
                "model_description": model_description,
                "model_version": model_version
            }
        )

        version_id = response.get("VersionId", "null")

        return jsonify({
            "message": "Model uploaded to S3 successfully",
            "model_name": model_name,
            "version": model_version,
            "s3_key": s3_key,
            "version_id": version_id
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


def get_model_status_s3(request):
    try:
        model_name = request.args.get("model_name")
        environment = request.args.get("environment", "Development")

        if not model_name:
            return jsonify({"error": "Missing model_name"}), 400

        prefix = f"{S3_FOLDER}{model_name}/"
        result = s3.list_object_versions(Bucket=S3_BUCKET_NAME, Prefix=prefix)

        versions = result.get("Versions", [])
        if not versions:
            return jsonify({"error": "No versions found for this model"}), 404

        latest = sorted(versions, key=lambda x: x["LastModified"], reverse=True)[0]

        return jsonify({
            "model_name": model_name,
            "status": "Deployed",
            "environment": environment,
            "s3_key": latest["Key"],
            "version_id": latest["VersionId"]
        }), 200

    except ClientError as ce:
        return jsonify({"error": str(ce)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
