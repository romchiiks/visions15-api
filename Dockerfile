FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY scripts/visions15ctl /usr/local/bin/visions15ctl

RUN chmod +x /usr/local/bin/visions15ctl

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
