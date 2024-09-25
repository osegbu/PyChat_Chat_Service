pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "osegbu/pychat-chat-service:latest"
    }
    stages {
        stage('Clone repository') {
            steps {
                git branch: 'main', url: 'https://github.com/osegbu/PyChat_Chat_Service.git'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image with the given tag
                    def app = docker.build("${DOCKER_IMAGE}", ".")
                }
            }
        }
        stage('Run Application and Health Check') {
            steps {
                script {
                    // Run the Docker container in detached mode with environment variables
                    def app = docker.image("${DOCKER_IMAGE}")
                    
                    app.run("-d -p 8001:8001 --name chat_service")

                    // Perform health check
                    def response = sh(
                        script: "curl --write-out %{http_code} --silent --output /dev/null http://localhost:8001/docs",
                        returnStdout: true
                    ).trim()

                    // Check if the response code is 200
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
                    // Stop and remove the Docker container after the health check
                    sh 'docker stop chat_service || true'
                    sh 'docker rm chat_service || true'
                }
            }
        }
    }
    post {
        always {
            // Clean up the Docker image to save space
            sh 'docker rmi ${DOCKER_IMAGE} || true'
        }
    }
}

