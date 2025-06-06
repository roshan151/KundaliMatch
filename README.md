# Request microservice
curl -X POST http://localhost:5000/upload \
  -F "metadata={\"name\":\"test\",\"email\":\"parshwa.shah@gmail.com\"}" \
  -F "images=@path/to/image1.jpg" \
  -F "images=@path/to/image2.png"

# If not using docker compose
1. docker build -t docker-love-bhagya-backend .

2. docker.io/roshancodeitup/love-bhagya:latest

3. docker build -t --platform linux/amd64 docker-love-bhagya-backend .

4. docker run --rm -p 8080:8080 docker.io/library/docker-love-bhagya-backend:latest

## EC2 Docker commands:
1. sudo yum install -y docker
2. docker login
3. sudo service docker start
4. sudo docker pull docker.io/roshancodeitup/love-bhagya:latest
5. sudo docker run --rm -p 8080:8080 docker.io/roshancodeitup/love-bhagya-backend-amd64:latest

<!-- sudo yum install nginx
sudo apt install certbot python3-certbot-nginx -y

Adding certs: https://certbot.eff.org/instructions?ws=webproduct&os=pip -->

Running multiple containers on EC2
sudo docker run -d --name lovebhagya-backend -p 8080:8080 docker.io/roshancodeitup/love-bhagya-backend-amd64:latest

Create docker-compose.yaml in EC2:
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

## Install docker compose:
1. sudo mkdir -p /usr/local/lib/docker/cli-plugins
2. sudo curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/3. 3. cli-plugins/docker-compose
4. sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

## Check docker version:
1. sudo docker compose version

cd to /usr/home/ssm-user


## Docker compose process:
1. docker compose build
- Do this with --platform linux/amd64 for EC2

2. docker tag and docker push images

3. Inside EC2 paste docker-compose-ec2-yml (keep name as docker-compose.yml)

4. docker pull 
-Pull both images, initially requires docker login -u <email> -p <token>

5. docker compose up -d

6. docker container ls
- List running docker containers

7. docker logs <container-id> -f
- watch logs

8. docker compose down
- Stop containers

NOTE: ON ec2 PRECEED COMMANDS WITH SUDO

## Edit NGINX config file
1. sudo nano /etc/nginx/conf.d/lovebhagya.com.conf
