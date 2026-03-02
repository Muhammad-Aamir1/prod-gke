resource "google_compute_network" "shared_vpc" {
  name                    = "gke-shared-vpc"
  auto_create_subnetworks = false
  routing_mode            = "GLOBAL"
}

resource "google_compute_subnetwork" "gke_subnet" {
  name                     = "gke-prod-subnet"
  ip_cidr_range            = "10.0.0.0/20"
  region                   = "us-central1"
  network                  = google_compute_network.shared_vpc.id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = "10.1.0.0/16"
  }
  secondary_ip_range {
    range_name    = "svc-ranges"
    ip_cidr_range = "10.2.0.0/20"
  }
}

# Cloud Router and NAT for private GKE nodes to reach the internet
resource "google_compute_router" "router" {
  name    = "gke2-router"
  region  = google_compute_subnetwork.gke_subnet.region
  network = google_compute_network.shared_vpc.id
}

resource "google_compute_router_nat" "nat" {
  name                               = "gke-nat"
  router                             = google_compute_router.router.name
  region                             = google_compute_router.router.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
