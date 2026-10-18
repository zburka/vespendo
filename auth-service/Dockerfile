FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY kapu ./kapu
COPY main.py .
COPY tools ./tools
RUN useradd -r -u 10001 kapu && mkdir /data && chown kapu /data
USER kapu
VOLUME /data
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
