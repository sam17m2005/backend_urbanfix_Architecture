FROM python:3.13-alpine

WORKDIR /app

RUN apk add --no-cache git gcc musl-dev libpq-dev git

COPY . /app

RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
    
CMD ["python3", "app.py"]