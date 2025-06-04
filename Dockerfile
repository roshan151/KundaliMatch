FROM python:3.11-slim

WORKDIR /app
#USER root
#RUN apt -y clean && apt -y update && apt-get install -y --reinstall ca-certificates && update-ca-certificates

COPY . .
#RUN apt-get install -y dnsutils git
RUN pip install setuptools --upgrade
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
EXPOSE 8080

CMD ["python", "match.py"]