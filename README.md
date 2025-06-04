# Build docker container
docker build -t flask-multipart .
docker run -p 5000:5000 flask-multipart

# Rquest microservice
curl -X POST http://localhost:5000/upload \
  -F "metadata={\"name\":\"test\",\"desc\":\"example\"}" \
  -F "images=@path/to/image1.jpg" \
  -F "images=@path/to/image2.png"

# Get schema
SELECT * FROM YOUR_DATABASE.YOUR_SCHEMA.MY_TABLE;

build image: docker build -t docker-love-bhagya-backend .
docker image name: docker.io/roshancodeitup/love-bhagya:latest