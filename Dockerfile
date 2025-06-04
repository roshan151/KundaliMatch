FROM python:3.11-slim

WORKDIR /app

COPY . .
RUN pip install setuptools --upgrade
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt
RUN git clone --recurse-submodules https://github.com/astrorigin/pyswisseph
EXPOSE 8080

CMD ["python", "match.py"]
