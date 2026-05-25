locals {
  environment_labels = merge(var.labels, {
    environment = var.environment
  })
}

module "vpc" {
  source = "../modules/vpc"

  name         = var.vpc_name
  routing_mode = var.routing_mode
}

moved {
  from = google_compute_network.shared_vpc
  to   = module.vpc.google_compute_network.this
}

module "subnet" {
  source = "../modules/subnet"

  name          = var.subnet_name
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network_id    = module.vpc.id
  pod_cidr      = var.pod_cidr
  svc_cidr      = var.svc_cidr
}

moved {
  from = google_compute_subnetwork.gke_subnet
  to   = module.subnet.google_compute_subnetwork.this
}

module "nat" {
  source = "../modules/nat"

  router_name = var.router_name
  nat_name    = var.nat_name
  region      = var.region
  network_id  = module.vpc.id
}

moved {
  from = google_compute_router.router
  to   = module.nat.google_compute_router.this
}

moved {
  from = google_compute_router_nat.nat
  to   = module.nat.google_compute_router_nat.this
}
