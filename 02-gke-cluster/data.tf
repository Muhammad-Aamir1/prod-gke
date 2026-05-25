data "google_compute_network" "shared_vpc" {
  name    = var.vpc_name
  project = var.vpc_project_id
}

data "google_compute_subnetwork" "gke_subnet" {
  name    = var.subnet_name
  region  = var.region
  project = var.vpc_project_id
}

data "google_project" "project" {
  project_id = var.project_id
}
