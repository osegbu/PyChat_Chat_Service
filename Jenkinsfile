pipeline {
    agent {
        docker {
            image 'docker:latest' // Use Docker-in-Docker image
            args '-v /var/run/docker.sock:/var/run/docker.sock' // Mount Docker socket to enable Docker commands
        }
    }
    
    environment {
        DOCKER_CREDENTIALS_ID = 'docker' // Docker credentials ID for DockerHub
        DOCKER_IMAGE = 'osegbu/PyChat_Chat_Service' // Docker image name
    }
    
    stages {
        stage('Clone Repository') {
            steps {
                git branch: 'main', url: 'https://github.com/osegbu/PyChat_Chat_Service'
            }
        }
        
        stage('Build Docker Image') {
            steps {
                script {
                    // Build Docker image
                    sh 'docker build -t ${DOCKER_IMAGE}:latest .'
                }
            }
        }
        
        stage('Push Docker Image') {
            steps {
                script {
                    // Push Docker image to DockerHub
                    docker.withRegistry('https://index.docker.io/v1/', DOCKER_CREDENTIALS_ID) {
                        sh 'docker push ${DOCKER_IMAGE}:latest'
                    }
                }
            }
        }
        
        stage('Run Tests') {
            steps {
                script {
                    // Run the Docker container
                    sh 'docker run -d --name chat_service -p 8001:8001 ${DOCKER_IMAGE}:latest'
                    
                    // Test if the application is up and running
                    def statusCode = sh(
                        script: "curl --write-out %{http_code} --silent --output /dev/null http://localhost:8001/docs",
                        returnStdout: true
                    ).trim()
                    
                    // Check if the status code is 200 (success)
                    if (statusCode != '200') {
                        error "Application did not start successfully, received HTTP status code: ${statusCode}"
                    }
                    
                    // Stop and remove the container after testing
                    sh 'docker stop chat_service'
                    sh 'docker rm chat_service'
                }
            }
        }
        
        stage('Deploy') {
            steps {
                echo 'Deploying application...'
                // Add your deployment steps here
            }
        }
    }
    
    post {
        always {
            // Clean up Docker images after build
            sh "docker rmi ${DOCKER_IMAGE}:latest || true"
        }
    }
}

