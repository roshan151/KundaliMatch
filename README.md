# Build docker container
docker build -t flask-multipart .
docker run -p 5000:5000 flask-multipart

# Rquest microservice
curl -X POST http://localhost:5000/upload \
  -F "metadata={\"name\":\"test\",\"email\":\"parshwa.shah@gmail.com\"}" \
  -F "images=@path/to/image1.jpg" \
  -F "images=@path/to/image2.png"

# Get schema
SELECT * FROM YOUR_DATABASE.YOUR_SCHEMA.MY_TABLE;

build image: docker build -t docker-love-bhagya-backend .
docker image name: docker.io/roshancodeitup/love-bhagya:latest

Docker Build:
docker build -t docker-love-bhagya-backend .

Docker run:
docker run --rm -p 8080:8080 docker.io/library/docker-love-bhagya-backend:latest


EC2 COMMANDS:
sudo yum install -y docker
docker login
sudo service docker start
sudo docker pull docker.io/roshancodeitup/love-bhagya:latest
sudo docker run --rm -p 8080:8080 docker.io/roshancodeitup/love-bhagya-backend-amd64:latest

sudo yum install nginx
sudo apt install certbot python3-certbot-nginx -y