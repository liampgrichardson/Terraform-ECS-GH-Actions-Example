FROM python:3.10

WORKDIR /app

EXPOSE 80

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY web_app_timestream_v25.py .
COPY app_helpers/ app_helpers/

ENTRYPOINT [ "python", "web_app_timestream_v25.py" ]
