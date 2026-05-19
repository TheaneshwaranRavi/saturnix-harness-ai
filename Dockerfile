FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN adduser --disabled-password --gecos "" saturnix

COPY saturnix_harness ./saturnix_harness
COPY examples ./examples
COPY README.md .

RUN mkdir -p /app/data /app/backups && chown -R saturnix:saturnix /app

EXPOSE 8088

USER saturnix

CMD ["uvicorn", "saturnix_harness.main:app", "--host", "0.0.0.0", "--port", "8088"]
