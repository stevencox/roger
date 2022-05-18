pipeline {
    agent {
        kubernetes {
            yaml '''
kind: Pod
metadata:
  name: kaniko
spec:
  containers:
  - name: jnlp
    workingDir: /home/jenkins/agent
  - name: kaniko
    workingDir: /home/jenkins/agent
    image: gcr.io/kaniko-project/executor:debug
    imagePullPolicy: Always
    resources:
      requests:
        cpu: "500m"
        memory: "1024Mi"
        ephemeral-storage: "768Mi"
      limits:
        cpu: "1000m"
        memory: "1024Mi"
        ephemeral-storage: "1024Mi"
    command:
    - /busybox/cat
    tty: true
    volumeMounts:
    - name: jenkins-docker-cfg
      mountPath: /kaniko/.docker
  volumes:
  - name: jenkins-docker-cfg
    projected:
      sources:
      - secret:
          name: rencibuild-imagepull-secret
          items:
            - key: .dockerconfigjson
              path: config.json
            '''
        }
    }
    stages {
        stage('Install') {
            steps {
                container(name: 'kaniko', shell: '/busybox/sh') {
                    sh '''
                    PYTHONPATH=dags /usr/bin/env python3 -m pip install --upgrade pip && \
                        PYTHONPATH=dags /usr/bin/env python3 -m pip install -r requirements.txt
                    '''
                }
            }
        }
        // stage('Test') {
        //     steps {
        //         container('agent-docker') {
        //             sh '''
        //             make test // won't work because "make" isn't installed currently
        //             '''
        //         }
        //     }
        // }
        stage('Build and Push Image') {
            environment {
                PATH = "/busybox:/kaniko:$PATH"
                DOCKERHUB_CREDS = credentials("${env.REGISTRY_CREDS_ID_STR}")
                DOCKER_REGISTRY = "${env.DOCKER_REGISTRY}"
                BUILD_NUMBER = "${env.BUILD_NUMBER}"
            }
            steps {
                container(name: 'kaniko', shell: '/busybox/sh') {
                    sh '''
                    /kaniko/executor --dockerfile Dockerfile \
                        --context . \
                        --verbosity debug \
                        --destination helxplatform/roger:new-jenkins-test-$BUILD_NUMBER
                    '''
                }
            }
        }
    }
}