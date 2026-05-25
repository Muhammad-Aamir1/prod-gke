project_id              = "staging-svc-project"
host_project_id         = "staging-host-project"
region                  = "us-central1"
environment             = "staging"
terraform_state_bucket  = "staging-tfstate"
cluster_name            = "staging-cluster"
release_channel         = "REGULAR"
enable_private_endpoint = false

standard_pool = {
  name           = "standard-pool"
  machine_type   = "e2-standard-4"
  min_node_count = 1
  max_node_count = 5
  labels = {
    "finops.tier" = "backend"
    "env"         = "staging"
  }
}
spot_pool = {
  name           = "spot-frontend-pool"
  machine_type   = "e2-standard-2"
  min_node_count = 1
  max_node_count = 8
  labels = {
    "finops.tier" = "frontend"
  }
}
