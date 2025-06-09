FROM python:3.11-slim

WORKDIR /app
#USER root
#RUN apt -y clean && apt -y update && apt-get install -y --reinstall ca-certificates && update-ca-certificates

#RUN apt-get install -y dnsutils git
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
COPY . .

EXPOSE 8080

CMD ["python", "backend.py"]