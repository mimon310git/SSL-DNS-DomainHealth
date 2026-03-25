FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml README.md main.py ./
COPY src ./src
COPY configs ./configs

RUN pip install --no-cache-dir .

ENTRYPOINT ["domain-sentinel"]
CMD ["run", "-c", "configs/domains.example.json", "--pretty-summary"]