FROM python:3.11-slim

LABEL maintainer="Michael Lastovich (Panda1847)"
LABEL description="ORACLE Penetration Hunter — AI-assisted red team mission orchestration"

WORKDIR /app

# System dependencies commonly needed by recon/scan tooling.
RUN apt-get update && apt-get install -y nmap && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN pip install --no-cache-dir -e .

VOLUME ["/app/missions", "/app/auth"]

ENTRYPOINT ["oracle"]
CMD ["--help"]
