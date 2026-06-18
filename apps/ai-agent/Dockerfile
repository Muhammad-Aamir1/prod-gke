FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl wget gnupg ca-certificates git && \
    curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/ && \
    curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash && \
    curl -sLO https://dl.google.com/dl/cloudsdk/channels/rapid/downloads/google-cloud-cli-516.0.0-linux-x86_64.tar.gz && \
    tar -xf google-cloud-cli-*.tar.gz -C /usr/local && /usr/local/google-cloud-sdk/install.sh --quiet && \
    ln -s /usr/local/google-cloud-sdk/bin/gcloud /usr/local/bin/gcloud && \
    rm -f google-cloud-cli-*.tar.gz && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8080
CMD ["python", "main.py"]
