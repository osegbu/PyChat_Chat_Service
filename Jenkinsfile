pipeline {
    agent {
        label 'docker-agent-alpine'
    }
    environment {
        DOCKER_IMAGE = "osegbu/PyChat_Chat_Service:latest"
    }
    stages {
        stage('Clone repository') {
            steps {
                git branch: 'main', url: 'git@github.com:osegbu/PyChat_Chat_Service.git'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    def app = docker.build("${DOCKER_IMAGE}", ".")
                }
            }
        }
        stage('Run Application and Health Check') {
            steps {
                script {
                    def app = docker.image(DOCKER_IMAGE)
                    app.run("-d -p 8001:8001 --name chat_service")

                    def response = sh(
                        script: "curl --write-out %{http_code} --silent --output /dev/null http://localhost:8001/docs", 
                        returnStdout: true
                    ).trim()

                    if (response == "200") {
                        echo "Application started successfully."
                    } else {
                        error "Health check failed. Application not running correctly."
                    }
                }
            }
        }
        stage('Cleanup') {
            steps {
                script {
                    sh 'docker stop chat_service'
                    sh 'docker rm chat_service'
                }
            }
        }
    }
    post {
        always {
            sh 'docker rmi ${DOCKER_IMAGE} || true'
        }
    }
}
