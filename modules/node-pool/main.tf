resource "google_container_node_pool" "this" {
  name       = var.name
  cluster    = var.cluster_id
  node_count = var.min_node_count

  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  management {
    auto_upgrade = var.auto_upgrade
    auto_repair  = var.auto_repair
  }

  node_config {
    image_type   = var.image_type
    machine_type = var.machine_type
    disk_type    = var.disk_type
    disk_size_gb = var.disk_size_gb
    spot         = var.spot
    labels       = var.labels

    dynamic "taint" {
      for_each = var.spot ? [1] : []
      content {
        key    = "cloud.google.com/gke-spot"
        value  = "true"
        effect = "NO_SCHEDULE"
      }
    }

    shielded_instance_config {
      enable_secure_boot = var.enable_secure_boot
    }

    workload_metadata_config {
      mode = var.workload_metadata_mode
    }
  }
}
