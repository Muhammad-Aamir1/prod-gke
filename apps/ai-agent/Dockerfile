FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl wget && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/ && \
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["python", "main.py"]
