resource "google_container_cluster" "this" {
  name     = var.name
  location = var.location

  network    = var.network
  subnetwork = var.subnetwork

  remove_default_node_pool = true
  initial_node_count       = 1

  ip_allocation_policy {
    cluster_secondary_range_name  = var.pod_range_name
    services_secondary_range_name = var.svc_range_name
  }

  datapath_provider = var.datapath_provider

  release_channel {
    channel = var.release_channel
  }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  node_locations = var.node_locations

  dynamic "private_cluster_config" {
    for_each = var.enable_private_nodes ? [1] : []
    content {
      enable_private_nodes    = var.enable_private_nodes
      enable_private_endpoint = var.enable_private_endpoint
      master_ipv4_cidr_block  = var.master_ipv4_cidr_block
    }
  }

  cluster_autoscaling {
    autoscaling_profile = var.autoscaling_profile
  }

  vertical_pod_autoscaling {
    enabled = var.enable_vpa
  }

  dynamic "gateway_api_config" {
    for_each = var.gateway_api_channel != null ? [1] : []
    content {
      channel = var.gateway_api_channel
    }
  }

  dynamic "maintenance_policy" {
    for_each = var.maintenance_start_time != null ? [1] : []
    content {
      recurring_window {
        start_time = var.maintenance_start_time
        end_time   = var.maintenance_end_time
        recurrence = var.maintenance_recurrence
      }
    }
  }

  resource_labels = var.labels
}
