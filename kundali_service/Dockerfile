FROM python:3.11.7-slim

WORKDIR /app

USER root
#RUN apt -y clean && apt -y update && apt-get install -y --reinstall ca-certificates && update-ca-certificates

#ARG GITHUB_PAT
#RUN apt-get install -y dnsutils git
#RUN apt-get install pyswisseph

RUN apt-get update && apt-get install -y gcc build-essential
RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install -r requirements.txt
#RUN git clone https://${GITHUB_PAT}@github.com/someshkar/panchanga.git
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]