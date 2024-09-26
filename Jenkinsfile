pipeline {
    agent any

    environment {
        IMAGE_NAME = 'osegbu/pychat-chat-service'
        SSH_USER = 'ec2-user'
        SSH_HOST = 'ec2-3-83-203-73.compute-1.amazonaws.com'
        SSH_KEY = '/path/to/my-ec2-01-RSA-key.pem'
        DEPLOYMENT_FILE_PATH = '~/deployment.yaml'
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
                        sh '''
                        ssh -i $SSH_KEY_PATH $SSH_USER@$SSH_HOST << EOF
                            sudo sed -i 's|image: .*|image: $IMAGE_NAME:$BUILD_NUMBER|' $DEPLOYMENT_FILE_PATH
                            sudo kubectl apply -f $DEPLOYMENT_FILE_PATH
                        EOF
                        '''
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

