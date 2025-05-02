pipeline {
    agent any

    environment {
        OLD_DIR = "${WORKSPACE}/Cross-Platform-Model-Development-and-Deployment-Pipeline"
        BACKUP_DIR = "${WORKSPACE}/prev"
        SERVICE_NAME = "flaskapp.service"
        REPO_URL = "https://github.com/koushikpr/Cross-Platform-Model-Development-and-Deployment-Pipeline.git"
    }

    stages {
        stage('Backup or Remove Old Project') {
            steps {
                script {
                    if (fileExists("${OLD_DIR}")) {
                        sh '''
                            mkdir -p "$BACKUP_DIR"
                            TIMESTAMP=$(date +%Y%m%d%H%M%S)
                            mv "$OLD_DIR" "$BACKUP_DIR/Cross-Platform-Model-Development-and-Deployment-Pipeline-$TIMESTAMP"
                        '''
                    }
                }
            }
        }

        stage('Clone Repo') {
            steps {
                sh '''
                    echo "Cloning into ${OLD_DIR}"
                    git clone "${REPO_URL}" "${OLD_DIR}"
                '''
            }
        }

        stage('Install Requirements') {
            steps {
                dir("${OLD_DIR}") {
                    sh "pip3 install -r requirements.txt"
                }
            }
        }

        stage('Restart Flask App') {
            steps {
                sh '''
                    echo "Restarting Flask service..."
                    sudo systemctl daemon-reexec
                    sudo systemctl restart "$SERVICE_NAME"
                '''
            }
        }
    }
}
