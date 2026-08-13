FROM python:3.13-alpine

WORKDIR /app

RUN apk add --no-cache git
RUN git clone https://github.com/FelipeAguilar302/backend_urbanfix.git .
RUN python3 -m venv .venv
ENV PATH="/app/.venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt
CMD ["python3", "app.py"]