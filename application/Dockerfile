FROM python:3.8-slim as release

WORKDIR /app

EXPOSE 80

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY web_app_timestream_v2.py .

ENTRYPOINT [ "python", "web_app_timestream_v2.py" ]
