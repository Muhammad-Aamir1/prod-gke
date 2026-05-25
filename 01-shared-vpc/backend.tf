terraform {
  backend "gcs" {
    # NOTE: Replace with your actual GCS bucket name
    # Bucket naming convention: <PROJECT_ID>-tfstate
    # Usage:
    #   1. Create the bucket:
    #      gsutil mb gs://<PROJECT_ID>-tfstate
    #   2. Enable versioning:
    #      gsutil versioning set on gs://<PROJECT_ID>-tfstate
    #   3. Run: terraform init -backend-config="bucket=<PROJECT_ID>-tfstate"
    #
    # Or uncomment the lines below and fill in your values:
    # bucket = "my-project-tfstate"
    # prefix = "01-shared-vpc"
  }
}
