FROM python:3.9-slim

WORKDIR /app

EXPOSE 80

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY web_app_timestream_v24.py .
COPY app_helpers/ app_helpers/

ENTRYPOINT [ "python", "web_app_timestream_v24.py" ]
