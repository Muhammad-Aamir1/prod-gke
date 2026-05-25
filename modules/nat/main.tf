resource "google_compute_router" "this" {
  name    = var.router_name
  region  = var.region
  network = var.network_id
}

resource "google_compute_router_nat" "this" {
  name                               = var.nat_name
  router                             = google_compute_router.this.name
  region                             = google_compute_router.this.region
  nat_ip_allocate_option             = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"
}
