pipeline {
    agent any

    environment {
        DOCKER_CREDENTIALS_ID = 'docker' // Jenkins credential ID for Docker Hub
        DOCKER_IMAGE = 'osegbu/PyChat_Chat_Service' // Your Docker Hub image name
    }

    stages {
        stage('Clone Repository') {
            steps {
                // Clone your repository
                git branch: 'main', url: 'https://github.com/osegbu/PyChat_Chat_Service'
            }
        }
        stage('Build Docker Image') {
            steps {
                script {
                    // Build the Docker image
                    docker.build(DOCKER_IMAGE)
                }
            }
        }
        stage('Push Docker Image') {
            steps {
                script {
                    // Login to Docker Hub
                    docker.withRegistry('https://index.docker.io/v1/', DOCKER_CREDENTIALS_ID) {
                        // Push the image to Docker Hub
                        docker.image(DOCKER_IMAGE).push()
                    }
                }
            }
        }
        stage('Run Tests') {
            steps {
                script {
                    // Run the Docker container and execute tests
                    def app = docker.image(DOCKER_IMAGE)
                    app.run("-d -p 8001:8001")
                    // Add your test commands here, e.g., using pytest
                    sh 'pytest'
                    // Optionally, stop and remove the container after tests
                    sh 'docker ps -q --filter "ancestor=${DOCKER_IMAGE}" | xargs docker stop'
                    sh 'docker ps -aq --filter "ancestor=${DOCKER_IMAGE}" | xargs docker rm'
                }
            }
        }
        stage('Deploy') {
            steps {
                script {
                    // Add your deployment steps here
                    echo 'Deploying application...'
                }
            }
        }
    }
    post {
        always {
            // Clean up Docker images
            sh "docker rmi ${DOCKER_IMAGE} || true"
        }
    }
}

