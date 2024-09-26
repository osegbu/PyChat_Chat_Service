pipeline {
    agent any

    environment {
        IMAGE_NAME = 'osegbu/pychat-chat-service'
        SSH_USER = 'ec2-user'
        SSH_HOST = 'ec2-100-26-193-126.compute-1.amazonaws.com'
        DEPLOYMENT_FILE_PATH = '~/chat-service-deployment.yaml'
    }

    stages {
        stage('Clone Repository') {
            steps {
                git branch: 'main', url: 'https://github.com/osegbu/PyChat_Chat_Service.git'
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker build -t $IMAGE_NAME:$BUILD_NUMBER .'
                }
            }
        }

        stage('Push Docker Image') {
            steps {
                script {
                    docker.withRegistry('https://index.docker.io/v1/', 'docker') {
                        sh 'docker push ${IMAGE_NAME}:${BUILD_NUMBER}'
                    }
                }
            }
        }

        stage('Deploy to k3s via SSH') {
            steps {
                script {
                    withCredentials([sshUserPrivateKey(credentialsId: 'my-ec2-ssh-key', 
                                                      keyFileVariable: 'SSH_KEY_PATH')]) {
			sh """
                        ssh -o StrictHostKeyChecking=no -i \$SSH_KEY_PATH \$SSH_USER@\${SSH_HOST} "
                            sudo sed -i 's|image: .*|image: $IMAGE_NAME:$BUILD_NUMBER|' $DEPLOYMENT_FILE_PATH; 
                            sudo kubectl apply -f $DEPLOYMENT_FILE_PATH
                        "
                        """
                    }
                }
            }
        }
    }

    post {
        always {
            sh 'docker rmi $IMAGE_NAME:$BUILD_NUMBER || true'
        }
    }
}

