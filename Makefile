# Environment selection: ENV=prod make shared-vpc (defaults to prod)
ENV ?= prod
REGION := us-central1

# Load environment-specific project IDs
HOST_PROJECT_ID := $(shell grep host_project_id environments/$(ENV)/01-shared-vpc.tfvars | head -1 | cut -d'=' -f2 | tr -d ' "')
PROJECT_ID := $(shell grep project_id environments/$(ENV)/02-gke-cluster.tfvars | head -1 | cut -d'=' -f2 | tr -d ' "')
CLUSTER_NAME := $(shell grep cluster_name environments/$(ENV)/02-gke-cluster.tfvars | head -1 | cut -d'=' -f2 | tr -d ' "')

.PHONY: all shared-vpc cluster argocd-bootstrap manifests \
        plan-shared-vpc plan-cluster get-credentials \
        argocd-password argocd-sync \
        destroy destroy-argocd destroy-manifests destroy-cluster destroy-shared-vpc \
        init-shared-vpc init-cluster fmt validate lint help

all: shared-vpc cluster argocd-bootstrap

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

# ─── ArgoCD / GitOps ───────────────────────────────────────────────

argocd-bootstrap: get-credentials
	@echo "=== Installing ArgoCD ==="
	kubectl create namespace argocd --dry-run=client -o yaml | kubectl apply -f -
	kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
	@echo "=== Waiting for ArgoCD to be ready ==="
	kubectl wait --for=condition=available --timeout=180s deployment/argocd-server -n argocd
	kubectl wait --for=condition=available --timeout=120s deployment/argocd-applicationset-controller -n argocd
	@echo "=== Applying ApplicationSets ==="
	kubectl apply -f 04-argocd/
	@echo "=== ArgoCD ready. Syncs automatically from Git. ==="
	@echo "=== UI: kubectl port-forward svc/argocd-server -n argocd 8080:443 ==="

manifests: argocd-bootstrap
	@echo "=== Manifests managed by ArgoCD — syncs automatically. ==="
	@echo "=== Status: argocd app list ==="

argocd-password:
	@echo "=== ArgoCD admin password ==="
	kubectl get secret argocd-initial-admin-secret -n argocd -o jsonpath="{.data.password}" | base64 -d
	@echo ""

argocd-sync: get-credentials
	@echo "=== Triggering ArgoCD sync for environment: $(ENV) ==="
	-argocd app sync prod-gke-$(ENV)
	@echo "=== Triggering monitoring sync ==="
	-argocd app sync prod-gke-monitoring

# ─── Destroy ───────────────────────────────────────────────────────

destroy-argocd: get-credentials
	@echo "=== Tearing down ArgoCD ==="
	-kubectl delete applicationsets -n argocd --all
	-kubectl delete applications -n argocd --all
	-kubectl delete namespace argocd

destroy-manifests: get-credentials
	@echo "=== Destroying Kubernetes manifests (via ArgoCD) ==="
	-kubectl delete applicationsets -n argocd --all 2>/dev/null
	-kubectl delete applications -n argocd --all 2>/dev/null
	-kubectl delete namespace prod-ns
	-kubectl delete namespace monitoring

destroy-cluster:
	@echo "=== Destroying GKE Cluster (env: $(ENV)) ==="
	cd 02-gke-cluster && terraform destroy -auto-approve -var-file=../environments/$(ENV)/02-gke-cluster.tfvars

destroy-shared-vpc:
	@echo "=== Destroying Shared VPC (env: $(ENV)) ==="
	cd 01-shared-vpc && terraform destroy -auto-approve -var-file=../environments/$(ENV)/01-shared-vpc.tfvars

destroy: destroy-argocd destroy-cluster destroy-shared-vpc
	@echo "=== All resources destroyed ==="

# ─── Utility ───────────────────────────────────────────────────────

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
	@echo "Infrastructure:"
	@echo "  all                Deploy everything (shared-vpc + cluster + argocd)"
	@echo "  shared-vpc         Deploy the Shared VPC networking layer"
	@echo "  cluster            Deploy the GKE cluster"
	@echo "  argocd-bootstrap   Install ArgoCD and apply ApplicationSets"
	@echo "  manifests          Same as argocd-bootstrap (legacy)"
	@echo ""
	@echo "ArgoCD / GitOps:"
	@echo "  argocd-password    Get ArgoCD admin password"
	@echo "  argocd-sync        Manually trigger ArgoCD sync for current env"
	@echo ""
	@echo "Planning:"
	@echo "  plan-shared-vpc    Plan Shared VPC changes"
	@echo "  plan-cluster       Plan GKE cluster changes"
	@echo ""
	@echo "Destroy:"
	@echo "  destroy            Tear down everything (reverse order)"
	@echo "  destroy-argocd     Remove ArgoCD + all K8s resources"
	@echo "  destroy-cluster    Destroy the GKE cluster only"
	@echo "  destroy-shared-vpc Destroy the Shared VPC only"
	@echo ""
	@echo "Utility:"
	@echo "  get-credentials    Fetch kubeconfig for current env"
	@echo "  fmt                Format all Terraform files"
	@echo "  validate           Validate all Terraform files"
	@echo "  lint               Run TFLint on all Terraform files"
	@echo ""
	@echo "Environments: dev, staging, prod (default: prod)"
	@echo ""
	@echo "Examples:"
	@echo "  make all               # Full prod deploy"
	@echo "  make all ENV=dev       # Full dev deploy"
	@echo "  make cluster ENV=staging    # Deploy staging cluster"
	@echo "  make argocd-bootstrap  # Bootstrap ArgoCD on prod cluster"
