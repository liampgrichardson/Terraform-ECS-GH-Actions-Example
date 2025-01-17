FROM python:3.8-slim as release

WORKDIR /app

EXPOSE 8080

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY web_app.py .

ENTRYPOINT [ "python", "web_app.py" ]
