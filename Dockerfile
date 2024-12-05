FROM python:3.8-slim as release

WORKDIR /app

EXPOSE 80

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY app.py .

ENTRYPOINT [ "python", "app.py" ]
