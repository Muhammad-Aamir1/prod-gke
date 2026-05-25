# Environment selection: ENV=prod make shared-vpc (defaults to prod)
ENV ?= prod
REGION := us-central1

# Load environment-specific project IDs
HOST_PROJECT_ID := $(shell grep host_project_id environments/$(ENV)/01-shared-vpc.tfvars | head -1 | cut -d'=' -f2 | tr -d ' "')
PROJECT_ID := $(shell grep project_id environments/$(ENV)/02-gke-cluster.tfvars | head -1 | cut -d'=' -f2 | tr -d ' "')
CLUSTER_NAME := $(shell grep cluster_name environments/$(ENV)/02-gke-cluster.tfvars | head -1 | cut -d'=' -f2 | tr -d ' "')

.PHONY: all init-shared-vpc init-cluster shared-vpc cluster manifests destroy-shared-vpc destroy-cluster destroy-manifests destroy fmt validate lint

all: shared-vpc cluster manifests

init-shared-vpc:
	@echo "=== Initializing shared-vpc Terraform (env: $(ENV)) ==="
	cd 01-shared-vpc && terraform init -backend-config="bucket=$(PROJECT_ID)-tfstate" -backend-config="prefix=$(ENV)/01-shared-vpc"

init-cluster:
	@echo "=== Initializing cluster Terraform (env: $(ENV)) ==="
	cd 02-gke-cluster && terraform init -backend-config="bucket=$(PROJECT_ID)-tfstate" -backend-config="prefix=$(ENV)/02-gke-cluster"

shared-vpc: init-shared-vpc
	@echo "=== Deploying Shared VPC (env: $(ENV)) ==="
	cd 01-shared-vpc && terraform apply -auto-approve -var-file=../environments/$(ENV)/01-shared-vpc.tfvars

cluster: init-cluster
	@echo "=== Deploying GKE Cluster (env: $(ENV)) ==="
	cd 02-gke-cluster && terraform apply -auto-approve -var-file=../environments/$(ENV)/02-gke-cluster.tfvars

plan-shared-vpc: init-shared-vpc
	@echo "=== Planning Shared VPC (env: $(ENV)) ==="
	cd 01-shared-vpc && terraform plan -var-file=../environments/$(ENV)/01-shared-vpc.tfvars

plan-cluster: init-cluster
	@echo "=== Planning GKE Cluster (env: $(ENV)) ==="
	cd 02-gke-cluster && terraform plan -var-file=../environments/$(ENV)/02-gke-cluster.tfvars

get-credentials:
	@echo "=== Fetching kubeconfig (env: $(ENV)) ==="
	gcloud container clusters get-credentials $(CLUSTER_NAME) --region=$(REGION) --project=$(PROJECT_ID)

manifests: get-credentials
	@echo "=== Deploying Kubernetes manifests (env: $(ENV)) ==="
	kubectl apply -f 03-k8s-manifests/namespaces.yaml
	kubectl apply -f 03-k8s-manifests/network-policies/
	kubectl apply -f 03-k8s-manifests/eso-store.yaml
	kubectl apply -f 03-k8s-manifests/apps/

destroy-manifests: get-credentials
	@echo "=== Destroying Kubernetes manifests ==="
	-kubectl delete -f 03-k8s-manifests/apps/
	-kubectl delete -f 03-k8s-manifests/network-policies/
	-kubectl delete -f 03-k8s-manifests/namespaces.yaml

destroy-cluster:
	@echo "=== Destroying GKE Cluster (env: $(ENV)) ==="
	cd 02-gke-cluster && terraform destroy -auto-approve -var-file=../environments/$(ENV)/02-gke-cluster.tfvars

destroy-shared-vpc:
	@echo "=== Destroying Shared VPC (env: $(ENV)) ==="
	cd 01-shared-vpc && terraform destroy -auto-approve -var-file=../environments/$(ENV)/01-shared-vpc.tfvars

destroy: destroy-manifests destroy-cluster destroy-shared-vpc
	@echo "=== All resources destroyed ==="

fmt:
	cd 01-shared-vpc && terraform fmt
	cd 02-gke-cluster && terraform fmt

validate: init-shared-vpc init-cluster
	cd 01-shared-vpc && terraform validate
	cd 02-gke-cluster && terraform validate

lint:
	@echo "=== Running TFLint ==="
	cd 01-shared-vpc && tflint --format compact 2>/dev/null || true
	cd 02-gke-cluster && tflint --format compact 2>/dev/null || true

help:
	@echo "Usage: make <target> ENV=<env>"
	@echo ""
	@echo "Targets:"
	@echo "  all                Deploy everything (shared-vpc + cluster + manifests)"
	@echo "  shared-vpc         Deploy the Shared VPC networking layer"
	@echo "  cluster            Deploy the GKE cluster"
	@echo "  manifests          Deploy Kubernetes manifests"
	@echo "  plan-shared-vpc    Plan Shared VPC changes"
	@echo "  plan-cluster       Plan GKE cluster changes"
	@echo "  destroy            Tear down everything"
	@echo ""
	@echo "Environments: dev, staging, prod (default: prod)"
	@echo ""
	@echo "Examples:"
	@echo "  make all               # Deploy prod"
	@echo "  make all ENV=dev       # Deploy dev"
	@echo "  make plan-cluster ENV=staging  # Plan staging changes"
	@echo "  make manifests        # Deploy K8s manifests to prod"
