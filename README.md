# Notes about Jenkins

## Introduction

In this document I have gathered some notes and snippets about my Jenkins workflow.

## How to install Jenkins

*Note: Contrary to what we'll do here, the "best practice" is to have a Jenkins manager(?) and
many runners(?) all on different isolated machines.*

Here we build a docker image that is based on Jenkins but has the following extra features:

* BlueOcean Plugin: A better UX compared to original Jenkins UI (but we'll see that we still have to do many things with the original UI)
* Docker plugin: That's right, we'll be running docker inside docker, both for building and testing images. The actual docker process will be in a separate container, named `dind` (docker in docker)—The compose file comes below.

So let's first make a `Dockerfile` with the following contents:

```Dockerfile
FROM jenkins/jenkins:2.289.2-lts-jdk11
USER root
RUN apt-get update && apt-get install -y apt-transport-https \
       ca-certificates curl gnupg2 \
       software-properties-common
RUN curl -fsSL https://download.docker.com/linux/debian/gpg | apt-key add -
RUN apt-key fingerprint 0EBFCD88
RUN add-apt-repository \
       "deb [arch=amd64] https://download.docker.com/linux/debian \
       $(lsb_release -cs) stable"
RUN apt-get update && apt-get install -y docker-ce-cli
USER jenkins
RUN jenkins-plugin-cli --plugins "blueocean:1.24.7 docker-workflow:1.26"

```

NOTE: Use latest Jenkins to avoid security issues. This is an outdated, unused Dockerfile.

The following docker compose can be used to launch Jenkins and DinD:


```yaml
version: "3"

volumes:
  jenkins-home:

services:
  docker:
    image: docker:dind
    container_name: jenkins-docker
    privileged: true
    environment:
      - DOCKER_TLS_CERTDIR=/certs
    volumes:
      - ./certs:/certs/client
      - jenkins-home:/var/jenkins_home
      - ./data:/var/lib/docker
    restart: always

  jenkins:
    image: jenkins-extended
    build:
      dockerfile: ./Dockerfile
      context: .
    container_name: jenkins-app
    environment:
      - DOCKER_HOST=tcp://docker:2376
      - DOCKER_CERT_PATH=/certs/client
      - DOCKER_TLS_VERIFY=1
      - JAVA_ARGS="-Xmx512m"
    volumes:
      - ./certs:/certs/client:ro
      - jenkins-home:/var/jenkins_home
    restart: always
    ports:
      - "127.0.0.1:1785:8080"
    depends_on:
      - docker
    deploy:
      resources:
        limits:
          memory: 600M
```

Below is an nginx configuration as a bare metal reverse proxy:

```nginx
server {
        listen 80;
        server_name ci.cakerobotics.com;
        return 301 https://$host$request_uri;
}

server {
        listen 443 ssl;
        server_name ci.cakerobotics.com;

        ssl_certificate /etc/letsencrypt/live/ci.cakerobotics.com/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/ci.cakerobotics.com/privkey.pem;

        location / {
                proxy_set_header        X-Real-IP       $remote_addr;
                proxy_set_header        X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header        X-Forwarded-Proto https;
                proxy_set_header        Host            $http_host;

                # the following enables websockets
                # proxy_http_version      1.1;
                # proxy_set_header        Upgrade        $http_upgrade;
                # proxy_set_header        Connection     "upgrade";

                # peer calls app
                proxy_pass      http://127.0.0.1:1785;
		client_max_body_size 100m;
        }
}
```

The volumes and mount points are self-explanatory. I don't remember why I used mounted directories too, rather than only volumes. It might be just random. Anyways, we usually don't need to do anything manual with the directories. Occassionally we will need to inspect the jenkins home volume (can't remember why though), which is easiest to do by attaching to the container:

```
docker exec -it -u root jenkins-app /bin/bash
```

Now we can run our thing:
```
docker compose up -d --build
docker compose logs -f jenkins-app
```

## Configuring

Just open the web app and config through it.

## Workflows

Here's a basic `Jenkinsfile` I use but many items depend on external systems. Also, I used an existing Keycloak to protect my registry, but that's an overkill. Anyways:

```jenkins
pipeline {
  agent any
  stages {
    stage('Build Docs') {
      steps {
        script {
          sh '${WORKSPACE}/docs/make.sh'
        }
        stash includes: '**/docs/index.html', name: 'docs'
      }
    }

    stage('Publish Docs') {
      steps {
        unstash 'docs'
        script {
          withCredentials([usernamePassword(credentialsId: 'jenkins-keycloak', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
            env.TOKEN = sh(script: '''
            curl -H "Content-Type: application/json" -d "{\\"username\\": \\"${USERNAME}\\", \\"password\\": \\"${PASSWORD}\\"}" https://utils.france-1.servers.cakerobotics.com/get-token
            ''', returnStdout: true)
            sh '''
            set +x
            echo "Using ${USERNAME}:*****"
            TEMPFILE=$(mktemp)
            curl -o ${TEMPFILE} -H "Authorization: Bearer ${TOKEN}" -F "index.html=@${WORKSPACE}/docs/index.html" https://utils.france-1.servers.cakerobotics.com/publish-api-doc/auth
            cat ${TEMPFILE} | grep Success
            set -x
            '''
          }
        }
      }
    }

    stage('Build') {
      steps {
        script {
          dockerImage = docker.build "images.cakerobotics.com/mostafa/auth:latest", "."
        }
      }
    }

    stage('Test') {
      steps {
        script {
          sh '${WORKSPACE}/run-tests.sh'
        }

      }
    }

    stage('Push') {
      steps {
        script {
          withDockerRegistry(credentialsId: 'jenkins-keycloak', url: 'https://images.cakerobotics.com/v2/') {
            dockerImage.push()
          }
        }

      }
    }

    stage('Deploy') {
      steps {
        script {
          withCredentials([usernamePassword(credentialsId: 'jenkins-keycloak', usernameVariable: 'USERNAME', passwordVariable: 'PASSWORD')]) {
            env.TOKEN = sh(script: '''
            curl -H "Content-Type: application/json" -d "{\\"username\\": \\"${USERNAME}\\", \\"password\\": \\"${PASSWORD}\\"}" https://utils.france-1.servers.cakerobotics.com/get-token
            ''', returnStdout: true)
            sh '''
            set +x
            echo "Using ${USERNAME}:*****"
            TEMPFILE=$(mktemp)
            curl -o ${TEMPFILE} -H "Content-Type: application/json" -H "Authorization: Bearer ${TOKEN}" -d \'{"service": "auth", "directory": "/services/cake"}\' https://utils.france-1.servers.cakerobotics.com/docker-compose-deliver
            cat ${TEMPFILE} | grep Success
            set -x
            '''
          }
        }
      }
    }
  }
}

```

Note: If you want to keep the keycloak-docker step, you should use [this extended image](https://github.com/ieggel/DockerRegistryKeycloakUserNamespaceMapper) for Jenkins.

## Deploying

See the folder "deployment-service" to find a relatively basic example for deploying service. This can still become simpler. A bash script invoked by SSH may be more than enough for your use case.

## Creating the Job

Use BlueOcean UI to create the job by linking a git repository.

## Git hooks

You may use plain HTTP hooks with "Multibranch Scan Webhook Trigger" plugin. To add a hook, go to the job, open "configure" page, go to "scan multibranch pipeline triggers", enable "scan by webhook". Define a token. This needs to have an authentication mechanism. I currently include a random string in the token, that is, my token looks like `app-wnolvbsra`. The final url will look like this:

https://ci.cakerobotics.com/multibranch-webhook-trigger/invoke?token=apps-wnolvbsra

You need to supply this to your git server as a push hook.
