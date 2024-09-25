pipeline {
    agent { label 'docker-agent-alpine' }

    environment {
        DOCKER_CREDENTIALS_ID = 'docker'
        DOCKER_IMAGE = 'osegbu/PyChat_Chat_Service'
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
                    docker.build(DOCKER_IMAGE)
                }
            }
        }
        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', DOCKER_CREDENTIALS_ID) {
                        docker.image(DOCKER_IMAGE).push()
                    }
                }
            }
        }
        stage('Run Tests') {
            steps {
                script {
                    def app = docker.image(DOCKER_IMAGE)
                    app.run("-d -p 8001:8001 --name chat_service")
                    
                    // Run pytest to execute the tests
                    sh 'pytest --maxfail=1 --disable-warnings'
                    
                    // Stop and remove the container by name
                    sh 'docker stop chat_service'
                    sh 'docker rm chat_service'
                }
            }
        }
        stage('Deploy') {
            steps {
                script {
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

