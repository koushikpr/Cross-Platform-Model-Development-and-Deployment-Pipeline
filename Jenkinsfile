pipeline {
    agent any

    environment {
        REPO_NAME = "Cross-Platform-Model-Development-and-Deployment-Pipeline"
        BACKUP_DIR = "${WORKSPACE}/prev"
        SERVICE_NAME = "flaskapp.service"
        REPO_URL = "https://github.com/koushikpr/Cross-Platform-Model-Development-and-Deployment-Pipeline.git"
    }

    stages {
        stage('Backup Existing Repo') {
            steps {
                script {
                    if (fileExists("${WORKSPACE}/${REPO_NAME}")) {
                        sh '''
                            mkdir -p "$BACKUP_DIR"
                            TIMESTAMP=$(date +%Y%m%d%H%M%S)
                            mv "$REPO_NAME" "$BACKUP_DIR/${REPO_NAME}-$TIMESTAMP"
                        '''
                    }
                }
            }
        }

        stage('Clone Repository') {
            steps {
                sh '''
                    echo "Cloning repo into workspace..."
                    git clone "${REPO_URL}"
                '''
            }
        }

        stage('Install Requirements') {
            steps {
                dir("${REPO_NAME}") {
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
