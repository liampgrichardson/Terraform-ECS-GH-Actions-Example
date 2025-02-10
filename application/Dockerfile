FROM python:3.10-slim

WORKDIR /app

EXPOSE 80

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY web_app_timestream_v2.py .
COPY app_helpers .

ENTRYPOINT [ "python", "web_app_timestream_v24.py" ]
