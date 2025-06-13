# Variables - replace these with your actual details
EC2_USER := ec2-user
EC2_HOST := your-ec2-public-ip-or-hostname
SSH_KEY := key.pem
DOCKERFILE := Dockerfile 
DOCKER_IMAGE_NAME := myapp
DOCKER_REGISTRY := your-dockerhub-or-ecr-url/your-image:tag
LOCAL_DOCKERFILE_DIR := /publish to artifactory/

# SSH command with key and user
SSH := ssh -i $(SSH_KEY) $(EC2_USER)@$(EC2_HOST)

.PHONY: setup-docker get-image run-container verify-container publish clean

VERSION = v0.2.3
BACKEND_IMAGE = kundalimatch-backend-service-amd64
KUNDALI_IMAGE = kundalimatch-kundali-service-amd64

publish:
	docker tag docker.io/library/$(BACKEND_IMAGE):latest docker.io/roshancodeitup/$(BACKEND_IMAGE):latest
	docker tag docker.io/roshancodeitup/$(BACKEND_IMAGE):latest docker.io/roshancodeitup/$(BACKEND_IMAGE):$(VERSION)
	docker tag docker.io/library/$(KUNDALI_IMAGE):latest docker.io/roshancodeitup/$(KUNDALI_IMAGE):latest
	docker tag docker.io/roshancodeitup/$(KUNDALI_IMAGE):latest docker.io/roshancodeitup/$(KUNDALI_IMAGE):$(VERSION)
	docker push docker.io/roshancodeitup/$(BACKEND_IMAGE):latest
	docker push docker.io/roshancodeitup/$(BACKEND_IMAGE):$(VERSION)
	docker push docker.io/roshancodeitup/$(KUNDALI_IMAGE):latest
	docker push docker.io/roshancodeitup/$(KUNDALI_IMAGE):$(VERSION)

# 1. Set up Docker on EC2
setup-docker:

	# 	docker push docker.io/roshancodeitup/$(BACKEND_IMAGE):latest
	# docker push docker.io/roshancodeitup/$(BACKEND_IMAGE):$(VERSION)
	@echo "Connecting to EC2 and installing Docker..."
	$(SSH) 'sudo yum update -y && \
		sudo yum install -y docker && \
		sudo service docker start && \
		sudo usermod -a -G docker $(EC2_USER) && \
		echo "Docker installed and started. Please log out and log back in to apply user group changes."'

# 2. Obtain Docker image
# Pull from registry
pull-image:
	@echo "Pulling Docker image from registry..."
	docker pull $(DOCKER_REGISTRY)

# Build image locally (on your machine or EC2 if needed)
build-image:
	@echo "Building Docker image..."
	docker build -t app/ $(DOCKERFILE)
# 3. Run the container
run-container:
	@echo "Running Docker container..."
	docker run -d -p 8080:80 --name $(DOCKER_IMAGE_NAME) $(DOCKER_IMAGE_NAME)

# Verify container is running
verify:
	@echo "Verifying running containers..."
	docker ps

# Optional: Clean up container
stop-container:
	docker stop $(DOCKER_IMAGE_NAME) || true
	docker rm $(DOCKER_IMAGE_NAME) || true

# Full setup flow: setup Docker, get image, run container
setup-all: setup-docker
	@echo "Please log out and log back in to apply Docker group changes, then run 'make get-image' and 'make run-container' as needed."

# Fetch image and run container in one step (if image is on registry)
deploy:
	make setup-docker
	make pull-image
	make run-container

