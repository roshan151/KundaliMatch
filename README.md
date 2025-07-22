# Design

The backend consits of three live microservices - `service-backend`, `service-kundali`, `service-sqlite`. Fourth one is currently work in progress - `service-mbti`. Each of these services run as a seperate docker container on an exclusive port. Frontend only communicates to `service-backend` and then `service-backend` communicates with `service-kundali` to get kundali score and `service-sqlite` to fetch and feed data to the SQL database.
Building micorservices helps in decoupling the code, reduces package interdependancies, and promotes modularity where components like `service-kundali` can be easily replaced with one with better features. 

`service-backend`: Hosted on port `8040`. Contains all endpoints needed by the frontend as well as the Destiny agent.

`service-sqlite`: Hosted on port `8030`. Provides an endpoint `/execute`, use this endpoint to run SQL queries.

`service-kundali`: Hosted on port `8000`. Provides a kundali score using input - date of birth, time of birth, and lat, long of birthplace.

## How to host services locally using Docker

Each microservice is hosted in its own docker container. Docker images installs required packages from `requirements.txt` file during build step, copies all required files, and runs handler `.py` file which exposes flask API endpoints to be pinged by otherservices. Each micorservice contains its own `Dockerfile`
Multiple microservices are orchestrated together using a docker compose `.yml` file.
There are multiple `docker-compose.yml` files in the repository, Use the one that specifies `DEPLOYMENT_ENV` as `local` for `backend-service`.

Step 1: Install docker app `https://www.docker.com/get-started/` 

Step 2: In docker app create API key and save it locally (Never Push an API key or secret to GIT).

Step 3: From terminal perform docker login using this api key: `docker login -u <username> -p <api-key>`

Step 4: From terminal install docker compose: `sudo yum install -y docker`

Step 5: While docker app is running, run docker build in root directory: `docker compose build`. This builds new docker images and needs to be done anytime 
there is a code change in one of the services.

Step 6: To run docker containers: `docker compose up -d`

Step 7: Check running docker containers: `docker containers ls`

Step 8: Check logs of a docker container: `docker logs <condtainer-id> -f`

Step 9: Use curl commands to test backend endpoints, some example commands are present in file `/docs/test-commands.txt`. Make sure to use `localhost` address.

Step 10: To stop all running containers: `docker compose down`

### If not using docker compose or building single service container

1. docker build -t docker-love-bhagya-backend .

2. docker tag <current-name> <docker-repo-address/new-name>:latest

3. docker run --rm -p 8080:8080 <image-name>:latest

## How to host services on ec2 instances:

### Key differences between local and EC2

1. On ec2 proceed commands with `sudo`

2. Pull images on EC2 from docker repository instead of building them like in local. These images still need to be build locally using `--platform linux/amd64` and then pushed to docker repository

## Install Docker on EC2:

1. sudo yum install -y docker

2. docker login -u <username> -p <api-key>

3. sudo service docker start

4. sudo docker pull docker.io/roshancodeitup/love-bhagya:latest

5. sudo docker run --rm -p 8080:8080 docker.io/roshancodeitup/love-bhagya-backend-amd64:latest

## Install docker compose on EC2:

1. Create new directory: `sudo mkdir -p /usr/local/lib/docker/cli-plugins`

2. Install docker compose from url: `sudo curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/3. 3. cli-plugins/docker-compose`

3. Change permissions for docker compose: `sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose`

4. Check docker version: `sudo docker compose version`

5. Change directory to /usr/home/ssm-user 

6. Create docker-compose.yaml in EC2:

```
sudo cat <<EOF > docker-compose.yml
services:
  backend-service:
    image: docker.io/roshancodeitup/kundalimatch-backend-service-amd64:latest
    ports:
      - "8080:8080"

  kundali-service:
    image: docker.io/roshancodeitup/kundalimatch-kundali-service-amd64:latest
    ports:
      - "8000:8000"
EOF
```
7. Pull images specified in docker compose: `docker pull <image-name>`

8. Run containers: `docker compose -up -d`

### If not using docker compose or building single service container for EC2

1. docker build -t docker-love-bhagya-backend .

2. docker tag <current-name> <docker-repository-address/name>:latest

3. docker build -t --platform linux/amd64 docker-love-bhagya-backend .

4. docker run --rm -p 8080:8080 docker.io/library/docker-love-bhagya-backend:latest

## Hosting using NginX
<!-- sudo yum install nginx
sudo apt install certbot python3-certbot-nginx -y

Adding certs: https://certbot.eff.org/instructions?ws=webproduct&os=pip -->

## Edit NGINX config file
1. sudo nano /etc/nginx/conf.d/lovebhagya.com.conf

## Encryption + Security June 14th
Run dockerfile with aws credentials (.env is removed) - credentials + secrets manager
docker run --rm -p 8080:8080 -v ~/.aws:/root/.aws:ro -e AWS_DEFAULT_REGION=us-east-2

