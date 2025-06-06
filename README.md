# Build docker container
docker build -t flask-multipart .
docker run -p 5000:5000 flask-multipart

# Request microservice
curl -X POST http://localhost:5000/upload \
  -F "metadata={\"name\":\"test\",\"email\":\"parshwa.shah@gmail.com\"}" \
  -F "images=@path/to/image1.jpg" \
  -F "images=@path/to/image2.png"


build image: docker build -t docker-love-bhagya-backend .
docker image name: docker.io/roshancodeitup/love-bhagya:latest

Docker Build:
docker build -t --platform linux/amd64 docker-love-bhagya-backend .

Docker run:
docker run --rm -p 8080:8080 docker.io/library/docker-love-bhagya-backend:latest


EC2 COMMANDS:
sudo yum install -y docker
docker login
sudo service docker start
sudo docker pull docker.io/roshancodeitup/love-bhagya:latest
sudo docker run --rm -p 8080:8080 docker.io/roshancodeitup/love-bhagya-backend-amd64:latest

Kundali service:
kundali-service-amd64:latest

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

Install docker compose:
sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/lib/docker/cli-plugins/docker-compose
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

Check docker version:
sudo docker compose version

Then:
sudo docker compose up -d

cd to /usr/home/ssm-user