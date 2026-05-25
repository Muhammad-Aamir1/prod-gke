project_id              = "prod-svc-project"
host_project_id         = "prod-host-project"
region                  = "us-central1"
environment             = "prod"
terraform_state_bucket  = "prod-tfstate"
cluster_name            = "prod-cluster"
release_channel         = "STABLE"
enable_private_endpoint = false

standard_pool = {
  name           = "standard-pool"
  machine_type   = "e2-standard-4"
  min_node_count = 2
  max_node_count = 8
  labels = {
    "finops.tier" = "backend"
    "env"         = "prod"
  }
}
spot_pool = {
  name           = "spot-frontend-pool"
  machine_type   = "e2-standard-2"
  min_node_count = 2
  max_node_count = 15
  labels = {
    "finops.tier" = "frontend"
  }
}
