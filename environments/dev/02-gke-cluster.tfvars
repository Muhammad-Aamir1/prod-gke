project_id              = "second-project-497312"
vpc_project_id          = "second-project-497312"
host_project_id         = "second-project-497312"
region                  = "us-central1"
environment             = "dev"
terraform_state_bucket  = "second-project-497312-tfstate"
cluster_name            = "dev-cluster"
vpc_name                = "gke-dev-vpc"
subnet_name             = "gke-dev-subnet"
release_channel         = "REGULAR"
enable_private_endpoint = false

standard_pool = {
  name           = "standard-pool"
  machine_type   = "e2-standard-2"
  min_node_count = 1
  max_node_count = 3
  labels = {
    "finops.tier" = "backend"
    "env"         = "dev"
  }
}
spot_pool = {
  name           = "spot-frontend-pool"
  machine_type   = "e2-standard-2"
  min_node_count = 1
  max_node_count = 3
  labels = {
    "finops.tier" = "frontend"
  }
}
