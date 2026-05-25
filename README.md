# prod-gke

A production-grade **Google Kubernetes Engine (GKE)** reference architecture with Shared VPC, Workload Identity, FinOps-optimized node pools, defense-in-depth security, and in-cluster Prometheus/Grafana monitoring.

## Architecture

```
                           Google Cloud Load Balancer (gke-l7-gxlb)
                           ├── HTTPS :443  ── ManagedCertificate + Cloud Armor WAF
                           └── HTTP  :80   ── 301 redirect → HTTPS
                                    │
                               [Gateway API]
                                    │
                          ┌─────────────────┐
                          │  prod-ns        │
                          │  Namespace      │
                          │  PSA: restricted│
                          └────────┬────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
      ┌────────▼────────┐ ┌───────▼────────┐ ┌────────▼────────┐
      │  Frontend Web   │ │  Backend API   │ │   Databases     │
      │  1-5 replicas   │→│  1 replica     │→│  Postgres + Redis│
      │  Express.js     │ │  Express.js    │ │  StatefulSet/DEP│
      │  Spot pool      │ │  Standard pool │ │  PVC / AOF      │
      │  HPA @ 70% CPU  │ │  backend-ksa   │ └─────────────────┘
      └─────────────────┘ └────────────────┘
               │                   │
               │    ┌──────────────┴──────────────┐
               │    │  GCP Secret Manager          │
               │    │  postgres-user/password      │
               │    └──────────────┬───────────────┘
               │                   ▲
               │         ┌─────────┴──────────┐
               │         │  External Secrets   │
               │         │  Operator (ESO)     │
               │         └────────────────────┘
               │
      ┌────────▼───────────────────────────────────────┐
      │            Monitoring (monitoring ns)            │
      │  ┌─────────────────┐      ┌──────────────────┐  │
      │  │   Prometheus    │──────│    Grafana        │  │
      │  │   StatefulSet   │◀─────│   LoadBalancer    │  │
      │  │   ClusterIP:9090│      │   :80 → :3000     │  │
      │  └─────────────────┘      └──────────────────┘  │
      └──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                      Infrastructure Layer                        │
│  ┌──────────────┐    ┌──────────────────┐    ┌────────────────┐ │
│  │  VPC Network │    │   GKE Cluster    │    │  Workload      │ │
│  │  Subnet / NAT│───▶│  Dataplane V2    │    │  Identity      │ │
│  │  Private     │    │  Private Nodes   │    │  backend-ksa   │ │
│  │  Google Access│   │  Release Channel │    │  → GCP SA      │ │
│  └──────────────┘    └──────────────────┘    └────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
prod-gke/
├── 01-shared-vpc/            # Terraform: VPC networking layer
│   ├── main.tf               # VPC, subnet, Cloud Router, Cloud NAT
│   ├── shared-vpc-iam.tf     # Shared VPC host/service attachment + IAM
│   ├── variables.tf           # All configuration inputs
│   ├── outputs.tf             # VPC ID, subnet self-link, project number
│   ├── provider.tf            # Google provider config
│   └── backend.tf             # GCS remote state backend
│
├── 02-gke-cluster/            # Terraform: GKE cluster layer
│   ├── main.tf                # Cluster, node pools, WI, secrets, Cloud Armor
│   ├── data.tf                # Data sources (VPC, subnet, project)
│   ├── variables.tf           # All configuration inputs
│   ├── outputs.tf             # Cluster endpoint, CA cert, pool names
│   ├── provider.tf            # Google + Random providers
│   ├── backend.tf             # GCS remote state backend
│   └── cloud-armor.tf         # WAF policy (disabled by default)
│
├── 03-k8s-manifests/          # Kubernetes: application layer
│   ├── namespaces.yaml        # Namespace + SA + ResourceQuota + LimitRange
│   ├── eso-store.yaml         # External Secrets Operator SecretStore
│   ├── network-policies/      # Defense-in-depth network policies
│   │   ├── 01-default-deny.yaml
│   │   ├── 02-allow-dns.yaml
│   │   ├── 03-app-routing.yaml
│   │   ├── 04-allow-gcp-apis.yaml
│   │   ├── 05-allow-frontend-ingress.yaml
│   │   └── 06-allow-monitoring-scrape.yaml
│   └── apps/                  # Application workloads
│       ├── 01-databases.yaml      # PostgreSQL StatefulSet + Redis Deployment
│       ├── 02-backend.yaml        # Backend API (Express.js + prom-client)
│       ├── 03-frontend.yaml       # Frontend web (Express.js + HPA)
│       ├── 04-gateway.yaml        # GKE Gateway API + ManagedCertificate
│       ├── 05-external-secrets.yaml   # ExternalSecret for DB creds
│       └── 06-pod-disruption-budgets.yaml  # PDBs for all workloads
│
├── 04-monitoring/             # Prometheus + Grafana in-cluster monitoring
│   ├── 00-namespace-rbac.yaml     # monitoring namespace + SA + ClusterRole
│   ├── 01-prometheus-config.yaml  # Prometheus scrape config (pods, nodes, kubelet)
│   ├── 02-prometheus.yaml         # Prometheus StatefulSet (10Gi PVC, ClusterIP)
│   ├── 03-grafana-config.yaml     # Grafana datasource + provisioned dashboards
│   └── 04-grafana.yaml            # Grafana Deployment (5Gi PVC, LoadBalancer)
│
├── apps/                      # Application source code
│   ├── backend/
│   │   ├── package.json       # express, pg, ioredis, prom-client
│   │   ├── server.js          # Health check, /metrics, /data endpoints
│   │   └── Dockerfile         # Multi-stage Node.js 20-alpine build
│   └── frontend/
│       ├── package.json       # express, http-proxy-middleware, prom-client
│       ├── server.js          # Proxies /api → backend, serves static files
│       ├── public/index.html  # Dashboard UI showing all service statuses
│       └── Dockerfile         # Multi-stage Node.js 20-alpine build
│
├── modules/                   # Reusable Terraform modules
│   ├── vpc/                   # google_compute_network
│   ├── subnet/                # google_compute_subnetwork + secondary ranges
│   ├── nat/                   # Cloud Router + Cloud NAT
│   ├── gke-cluster/           # GKE cluster with Dataplane V2, WI, VPA
│   ├── node-pool/             # Node pool with autoscaling, shielded nodes
│   ├── workload-identity/     # GCP SA + Workload Identity binding
│   ├── secrets/               # Random password + Secret Manager secrets
│   └── cloud-armor/           # Cloud Armor WAF policy (disabled by default)
│
├── environments/              # Multi-environment configs
│   ├── dev/
│   │   ├── 01-shared-vpc.tfvars
│   │   └── 02-gke-cluster.tfvars
│   ├── staging/
│   │   ├── 01-shared-vpc.tfvars
│   │   └── 02-gke-cluster.tfvars
│   └── prod/
│       ├── 01-shared-vpc.tfvars
│       └── 02-gke-cluster.tfvars
│
├── Makefile                   # Orchestration: deploy/manage/destroy
├── .gitignore                 # Ignore .terraform/, *.tfstate, etc.
└── README.md                  # This file
```

## Quick Start

### Prerequisites

- Google Cloud Platform account with billing enabled
- Owner/Editor access to at least one GCP project
- Tools installed: `gcloud`, `terraform` >= 1.5, `kubectl`, `docker`
- Enabled APIs:
  - `container.googleapis.com`
  - `secretmanager.googleapis.com`
  - `cloudresourcemanager.googleapis.com`
  - `artifactregistry.googleapis.com`

### 1. Create Terraform State Bucket

```bash
gsutil mb gs://<YOUR_PROJECT_ID>-tfstate
gsutil versioning set on gs://<YOUR_PROJECT_ID>-tfstate
```

### 2. Configure Environment

```bash
# Edit the environment tfvars with your project IDs
vim environments/prod/01-shared-vpc.tfvars
vim environments/prod/02-gke-cluster.tfvars
```

### 3. Deploy Infrastructure

```bash
# Step 1: Networking (VPC, subnet, Cloud NAT)
make shared-vpc ENV=prod

# Step 2: GKE cluster + node pools + Workload Identity + secrets
make cluster ENV=prod
```

### 4. Build and Push Application Images

```bash
# Create Artifact Registry repository
gcloud artifacts repositories create app-images \
  --repository-format=docker \
  --location=us-central1

# Configure Docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build and push backend
docker build -t us-central1-docker.pkg.dev/<PROJECT_ID>/app-images/backend:latest apps/backend
docker push us-central1-docker.pkg.dev/<PROJECT_ID>/app-images/backend:latest

# Build and push frontend
docker build -t us-central1-docker.pkg.dev/<PROJECT_ID>/app-images/frontend:latest apps/frontend
docker push us-central1-docker.pkg.dev/<PROJECT_ID>/app-images/frontend:latest
```

### 5. Deploy Applications

```bash
# Get cluster credentials
make get-credentials ENV=prod

# Step 3: Deploy K8s manifests (namespace, network policies, apps)
make manifests ENV=prod
```

### 6. Deploy Monitoring Stack

```bash
# Deploy Prometheus + Grafana
kubectl apply -f 04-monitoring/

# Get Grafana external IP
kubectl get svc grafana -n monitoring -w
```

### 7. Set Up DNS (Optional)

Update your domain's DNS records to point to the external IP of the Gateway:

```bash
kubectl get gateway external-http-gw -n prod-ns
```

Then update the `domains` field in `03-k8s-manifests/apps/04-gateway.yaml` with your actual domain and re-apply.

## Application Architecture

### Backend API (`apps/backend/`)

Express.js server with three endpoints:
- `GET /health` — Returns status with PostgreSQL and Redis connectivity checks
- `GET /data` — Queries PostgreSQL and returns a sample row
- `GET /metrics` — Prometheus metrics via `prom-client` (default metrics + event loop lag)

Environment variables: `PGHOST`, `PGUSER`, `PGPASSWORD`, `PGDATABASE`, `REDIS_HOST`

### Frontend Web (`apps/frontend/`)

Express.js server that:
- Proxies `/api/*` to the backend via `http-proxy-middleware`
- Serves a static dashboard (`public/index.html`) showing real-time status of all services
- Exposes `GET /metrics` and `GET /health` endpoints

### Database Layer (`03-k8s-manifests/apps/01-databases.yaml`)

- **PostgreSQL**: StatefulSet with 10Gi PVC, `pg_isready` probes, `restricted` Pod Security
- **Redis**: Deployment with AOF persistence, TCP probes, `emptyDir` for data

## Monitoring Stack

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│  monitoring namespace                                      │
│                                                            │
│  ┌──────────────┐         ┌──────────────┐                │
│  │  Prometheus   │◄────────│  Grafana     │                │
│  │  StatefulSet  │────────►│  LoadBalancer│                │
│  │  ClusterIP:90 │ scrape  │  :80 → :3000 │                │
│  └──────┬───────┘         └──────────────┘                │
│         │                                                 │
│         │ Scrape targets:                                  │
│         │  • kubernetes-pods (via prometheus.io annotations)│
│         │  • kubernetes-nodes (cAdvisor metrics)           │
│         │  • kubernetes-kubelet (/metrics/cadvisor)        │
│         │  • prometheus itself (localhost:9090)             │
│         └─────────────────────────────────────────────────┘
└────────────────────────────────────────────────────────────┘
```

### Prometheus (`04-monitoring/`)

- **Type**: StatefulSet with 10Gi PVC, 7-day retention
- **Version**: `prom/prometheus:v2.53.0`
- **Service**: ClusterIP on port 9090
- **Scrape Jobs**:
  - `prometheus` — Self-scrape
  - `kubernetes-nodes` — Node-level metrics via cAdvisor
  - `kubernetes-pods` — Pod-level metrics (auto-discovers pods with `prometheus.io/scrape: "true"` annotation)
  - `kubernetes-kubelet` — Kubelet cAdvisor metrics over HTTPS

Resources: requests 200m CPU / 512Mi memory, limits 500m CPU / 1Gi memory.

### Grafana (`04-monitoring/`)

- **Type**: Deployment with 5Gi PVC
- **Version**: `grafana/grafana:11.0.0`
- **Service**: LoadBalancer on port 80 → 3000
- **Credentials**: `admin` / `prom-operator`
- **Provisioned Datasources**: Prometheus (auto-connected to `http://prometheus:9090`)
- **Provisioned Dashboards**:

#### 1. Kubernetes Cluster Dashboard
Sections: Cluster Overview, Cluster Resources (CPU/Memory/Network by node), Namespace Resources, Container Resources (CPU/Memory/Throttling by pod), Scrape Targets & Health

#### 2. prod-gke Application Dashboard
Sections: Application Overview (CPU, Memory, Heap %, Active Handles/Requests, Event Loop Lag, Process RSS, Node.js Instances), Node.js Memory & GC (Heap Total vs Used, Heap Space Breakdown, GC Rate/Count, External Memory), Event Loop & Concurrency (Event Loop Latency p50/p90/p99, Active Handles/Requests, Libuv Threads)

### Network Policy for Monitoring

`allow-prometheus-scrape` allows inbound traffic on port 8080 from the `monitoring` namespace to pods labeled `app: backend` or `app: frontend`.

### Accessing Grafana

```bash
# Get external IP
kubectl get svc grafana -n monitoring

# Port-forward (alternative)
kubectl port-forward svc/grafana -n monitoring 8080:80
# Visit http://localhost:8080, login: admin / prom-operator
```

## Key Features

### Security

| Feature | Implementation |
|---------|---------------|
| **Shared VPC** | Network in host project, cluster in service project — least privilege isolation |
| **Private Nodes** | No public IPs on nodes, Cloud NAT for egress |
| **Dataplane V2** | eBPF-based networking (Cilium), no iptables performance tax |
| **Workload Identity** | No GCP service account keys — pods impersonate IAM via K8s SA |
| **Pod Security Admission** | `restricted` level enforced — containers can't run as root |
| **Seccomp + Capabilities** | `RuntimeDefault` seccomp, all capabilites dropped, no privilege escalation |
| **NetworkPolicies** | Default-deny ingress + egress, explicit allow rules only |
| **Shielded Nodes** | Secure boot enabled on all nodes |
| **Cloud Armor WAF** | Rate limiting and OWASP protection at the edge (disabled by default) |
| **External Secrets** | Database credentials from GCP Secret Manager, never in YAML |

### FinOps (Cost Optimization)

| Feature | Savings |
|---------|---------|
| **Spot nodes for frontend** | 60-91% discount vs on-demand |
| **Cluster autoscaling** | `OPTIMIZE_UTILIZATION` profile — aggressive scale-down |
| **HPA on frontend** | 1-5 replicas based on CPU |
| **Resource requests/limits** | Every container has CPU/memory bounds |
| **e2 machine series** | Cost-optimized general-purpose VMs |
| **GKE usage metering** | Export to BigQuery for chargeback (opt-in) |

### Reliability

| Feature | Implementation |
|---------|---------------|
| **Topology spread** | Spread constraints for frontend across zones |
| **PodDisruptionBudgets** | At least 1 replica for each workload always available |
| **Readiness + Liveness probes** | Every workload has both |
| **Maintenance window** | Weekends 02:00-06:00 UTC |
| **Release channel** | `STABLE` for production — managed upgrades |
| **Auto-repair + Auto-upgrade** | Node pools self-heal and update |
| **Stateful Postgres** | PersistentVolumeClaim with 10Gi disk, pg_isready probes |
| **Redis AOF** | Append-only file persistence enabled |

## Environment Strategy

The repo supports **dev/staging/prod** environments via separate `tfvars` files:

| Setting | dev | staging | prod |
|---------|-----|---------|------|
| Cluster name | `dev-cluster` | `staging-cluster` | `prod-cluster` |
| Release channel | `REGULAR` | `REGULAR` | `STABLE` |
| Machine type (standard) | e2-standard-2 | e2-standard-4 | e2-standard-4 |
| Min nodes (standard) | 1 | 1 | 2 |
| Max nodes (spot) | 3 | 8 | 15 |
| CIDR base (subnet/pods/svc) | 10.64.x.x / 10.65.x.x / 10.66.x.x | 10.32.x.x | 10.0.x.x |

Each environment uses its own GCS state prefix: `dev/01-shared-vpc`, `staging/01-shared-vpc`, etc.

## Deployment Order

The layers must be deployed in order:

```
01-shared-vpc  →  02-gke-cluster  →  03-k8s-manifests  →  04-monitoring
  (network)        (cluster)          (apps)               (monitoring)
```

And destroyed in reverse:

```
04-monitoring  →  03-k8s-manifests  →  02-gke-cluster  →  01-shared-vpc
```

## Terraform State

Backend: **GCS** (not local).

```bash
# Initialize with backend config:
cd 01-shared-vpc
terraform init -backend-config="bucket=<PROJECT_ID>-tfstate" -backend-config="prefix=prod/01-shared-vpc"

cd 02-gke-cluster
terraform init -backend-config="bucket=<PROJECT_ID>-tfstate" -backend-config="prefix=prod/02-gke-cluster"
```

The `prefix` should match the environment + module name. Backend config is passed at init time so the same Terraform code works across environments.

## Node Pool Design

| Pool | Type | Machine | Scaling | Labels | Taints |
|------|------|---------|---------|--------|--------|
| `standard-pool` | On-demand | e2-standard-4 (4 vCPU, 16GB) | 2-8 | `finops.tier=backend`, `env=prod` | None |
| `spot-frontend-pool` | Spot | e2-standard-2 (2 vCPU, 8GB) | 2-15 | `finops.tier=frontend` | `gke-spot=true:NO_SCHEDULE` |

Workload placement:
- **Frontend** → spot pool via `nodeSelector` + toleration of spot taint
- **Backend/DBs** → standard pool via `nodeSelector`

## Network Policies

The policy model is **default-deny with explicit allow**:

| Policy | Direction | Purpose |
|--------|-----------|---------|
| `default-deny-all` | Ingress + Egress | Baseline — blocks everything |
| `allow-dns-egress` | Egress | CoreDNS + Workload Identity metadata server |
| `allow-gcp-api-access` | Egress | GCP APIs via Private Google Access IPs |
| `allow-frontend-ingress` | Ingress | Allow inbound traffic to frontend from load balancer |
| `allow-frontend-to-backend` | Ingress | Frontend → Backend on :8080 |
| `allow-backend-to-dbs` | Ingress | Backend → Postgres (:5432) / Redis (:6379) |
| `allow-frontend-egress` | Egress | Frontend → Backend on :8080 |
| `allow-backend-egress` | Egress | Backend → Postgres/Redis |
| `allow-prometheus-scrape` | Ingress | Prometheus from `monitoring` ns → apps on :8080 |

## Security Context Compliance

All pods meet the Kubernetes `restricted` Pod Security Standard:

```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: <image-specific UID>
  seccompProfile:
    type: RuntimeDefault
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
```

## Secrets Management

Password flow:

```
Terraform (random_password)
  → GCP Secret Manager (postgres-password, postgres-user)
    → External Secrets Operator (syncs to K8s Secret)
      → Postgres StatefulSet (envFrom secretRef)
```

No secrets in YAML files, no K8s Secrets created manually, no GCP SA keys in the cluster.

## Terraform Modules

### vpc
Creates a VPC with `auto_create_subnetworks = false` and configurable routing mode (default: `GLOBAL`).

### subnet
Creates a subnet with `private_ip_google_access = true` and two secondary IP ranges for GKE pods and services.

### nat
Creates a Cloud Router and Cloud NAT with automatic IP allocation for outbound connectivity from private nodes.

### gke-cluster
Creates a GKE cluster with:
- Dataplane V2 (eBPF/Cilium) for advanced networking
- Workload Identity pool (`<project>.svc.id.goog`)
- Private nodes (optional private endpoint)
- Cluster autoscaling with configurable profile
- Vertical Pod Autoscaling (optional)
- Gateway API (standard channel)
- Release channel for managed upgrades
- Maintenance window (recurring)
- Resource labels

### node-pool
Creates a node pool with:
- Autoscaling (min/max node count)
- Auto-upgrade and auto-repair
- Shielded instances (secure boot)
- Spot VM support with auto-taint
- Workload metadata config (GKE_METADATA)
- Configurable image type, disk type/size

### workload-identity
Creates a GCP service account and binds it to a Kubernetes service account via Workload Identity, enabling pods to impersonate IAM roles without service account keys.

### secrets
Creates:
- A random password for PostgreSQL
- Two Secret Manager secrets (`postgres-password`, `postgres-user`)
- IAM bindings granting the workload identity SA access to read secrets

### cloud-armor
Disabled by default. Provides a configurable Cloud Armor WAF security policy with rate limiting rules.

## Cost Estimates (Approximate)

| Component | Estimated Monthly Cost |
|-----------|----------------------|
| GKE cluster fee | $73 (flat per cluster) |
| Standard pool (2 nodes) | ~$140 |
| Spot frontend pool (2 nodes) | ~$10-20 |
| Cloud NAT | ~$5 |
| Load Balancer | ~$20 |
| Cloud Armor WAF | $5-10 |
| Persistent disks (Postgres 10Gi + Prometheus 10Gi + Grafana 5Gi) | ~$2 |
| **Total (prod, minimum)** | **~$260-280/month** |

## Useful Commands

```bash
# Deploy everything
make all ENV=prod

# Plan changes
make plan-shared-vpc ENV=prod
make plan-cluster ENV=prod

# Get cluster credentials
make get-credentials ENV=prod

# Destroy everything
make destroy ENV=prod

# Tear down specific layers manually
kubectl delete -f 04-monitoring/
make destroy-manifests ENV=prod
make destroy-cluster ENV=prod
make destroy-shared-vpc ENV=prod

# Port-forward to access services
kubectl port-forward svc/frontend-svc -n prod-ns 8080:80
kubectl port-forward svc/grafana -n monitoring 8080:80
```
