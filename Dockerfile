FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 BOCALI_DATA_DIR=/data
WORKDIR /app
COPY requirements-hosted.txt ./
RUN pip install --no-cache-dir -r requirements-hosted.txt && \
    groupadd -g 10001 bocali && useradd -u 10001 -g 10001 -M -s /usr/sbin/nologin bocali
COPY . .
EXPOSE 8000
ENTRYPOINT ["python", "container_start.py"]
