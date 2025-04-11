import paramiko
from flask import jsonify

FEDORA_PLAYBOOKS_DIR = "/home/aman/Desktop/Cross-Platform-Model-Development-and-Deployment-Pipeline/ansible/configurations/"
LIBRARY_PLAYBOOKS_DIR = "/home/aman/Desktop/Cross-Platform-Model-Development-and-Deployment-Pipeline/ansible/library/"

def deploy_fedora(request):
    try:
        data = request.json
        server_ip = data.get("server_ip")
        ssh_user = data.get("ssh_user")
        ssh_password = data.get("ssh_password")
        selected_libraries = data.get("libraries", [])

        if not server_ip or not ssh_user or not ssh_password:
            return jsonify({"error": "Missing required SSH details"}), 400

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(server_ip, username=ssh_user, password=ssh_password)
        except Exception as e:
            return jsonify({"error": f"SSH Connection failed: {str(e)}"}), 500

        ssh.exec_command("sudo su")
        ssh.exec_command("which ansible || dnf install -y ansible")

        jupyter = f"{FEDORA_PLAYBOOKS_DIR}jupyter-setup.yml"
        ssh.exec_command(f"ansible-playbook {jupyter}")

        for lib in selected_libraries:
            lib_playbook = f"{LIBRARY_PLAYBOOKS_DIR}{lib}.yml"
            ssh.exec_command(f"ansible-playbook {lib_playbook}")

        ssh.close()

        return jsonify({"message": "Fedora Server setup complete"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
