resource "google_compute_subnetwork" "this" {
  name                     = var.name
  ip_cidr_range            = var.ip_cidr_range
  region                   = var.region
  network                  = var.network_id
  private_ip_google_access = true

  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = var.pod_cidr
  }

  secondary_ip_range {
    range_name    = "svc-ranges"
    ip_cidr_range = var.svc_cidr
  }
}
