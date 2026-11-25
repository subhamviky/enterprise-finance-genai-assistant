# The landscape's foundation on Google Cloud, free tier only (hub design note GCP-01). Applied once,
# before the five services, by the person who owns the project (later changes through CI):
#
#   APIs            the services the landscape uses, enabled
#   images          ONE Artifact Registry repository for all five images, a cleanup policy keeping
#                   the free 0.5 GB (the newest few versions of each image)
#   firestore       the project's one free database, "(default)", shared: each service keeps its own
#                   collections (o2c, audit, recon, genai)
#   state           a Cloud Storage bucket for the Terraform state of every stack (5 GB free, US region)
#   deploy          GitHub Actions deploys through Workload Identity Federation: no JSON key exists.
#                   Only the listed repositories of the owner may use it.
#   budget          an alert at a small amount, so a surprise is an e-mail, not a bill
#   gemini key      the secret the gemini_api profile reads; its VALUE is added by hand, never here
#
# Nothing secret is in this configuration or its state.

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 8.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

data "google_project" "this" {}

locals {
  labels = { landscape = "finance-ai", managed-by = "terraform" }
  apis = ["run.googleapis.com", "firestore.googleapis.com", "pubsub.googleapis.com", "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com", "cloudscheduler.googleapis.com", "compute.googleapis.com", "iam.googleapis.com",
    "iamcredentials.googleapis.com", "sts.googleapis.com", "cloudbilling.googleapis.com", "billingbudgets.googleapis.com",
  "storage.googleapis.com", "logging.googleapis.com"]
  # what the CI's deployer may do: deploy the stacks and their services, nothing beyond the project
  deployer_roles = ["roles/run.admin", "roles/artifactregistry.writer", "roles/iam.serviceAccountUser",
    "roles/iam.serviceAccountAdmin", "roles/resourcemanager.projectIamAdmin", "roles/pubsub.admin",
    "roles/cloudscheduler.admin", "roles/secretmanager.admin", "roles/compute.admin", "roles/datastore.owner",
  "roles/storage.admin"]
}

resource "google_project_service" "apis" {
  for_each           = toset(local.apis)
  service            = each.value
  disable_on_destroy = false
}

# ------------------------------------------------------------------ images
resource "google_artifact_registry_repository" "landscape" {
  repository_id = "landscape"
  location      = var.region
  format        = "DOCKER"
  labels        = local.labels

  cleanup_policy_dry_run = false
  cleanup_policies {
    id     = "keep-newest"
    action = "KEEP"
    most_recent_versions {
      keep_count = var.images_kept
    }
  }
  cleanup_policies {
    id     = "delete-older"
    action = "DELETE"
    condition {
      older_than = "604800s"
    }
  }
  depends_on = [google_project_service.apis]
}

# ------------------------------------------------------------------ the one free Firestore database
resource "google_firestore_database" "default" {
  name                    = "(default)"
  location_id             = var.region
  type                    = "FIRESTORE_NATIVE"
  concurrency_mode        = "OPTIMISTIC" # the E2A adapters write with update-time preconditions
  delete_protection_state = "DELETE_PROTECTION_DISABLED"
  deletion_policy         = "DELETE" # terraform destroy before the trial ends leaves nothing behind
  depends_on              = [google_project_service.apis]
}

# ------------------------------------------------------------------ Terraform state
resource "google_storage_bucket" "state" {
  name                        = "${var.project_id}-tfstate"
  location                    = upper(var.region)
  uniform_bucket_level_access = true
  public_access_prevention    = "enforced"
  force_destroy               = true
  labels                      = local.labels
  versioning {
    enabled = true
  }
  lifecycle_rule {
    condition {
      num_newer_versions = 5
    }
    action {
      type = "Delete"
    }
  }
}

# ------------------------------------------------------------------ GitHub Actions, without a key
resource "google_iam_workload_identity_pool" "github" {
  workload_identity_pool_id = "github"
  display_name              = "GitHub Actions"
  depends_on                = [google_project_service.apis]
}

resource "google_iam_workload_identity_pool_provider" "github" {
  workload_identity_pool_id          = google_iam_workload_identity_pool.github.workload_identity_pool_id
  workload_identity_pool_provider_id = "github-oidc"
  display_name                       = "GitHub OIDC"
  attribute_mapping = {
    "google.subject"             = "assertion.sub"
    "attribute.repository"       = "assertion.repository"
    "attribute.repository_owner" = "assertion.repository_owner"
    "attribute.ref"              = "assertion.ref"
  }
  # only the owner's repositories; and only those listed may impersonate the deployer (below)
  attribute_condition = "assertion.repository_owner == '${var.github_owner}'"
  oidc {
    issuer_uri = "https://token.actions.githubusercontent.com"
  }
}

resource "google_service_account" "deployer" {
  account_id   = "landscape-deployer"
  display_name = "GitHub Actions deployer of the landscape"
}

resource "google_project_iam_member" "deployer" {
  for_each = toset(local.deployer_roles)
  project  = var.project_id
  role     = each.value
  member   = "serviceAccount:${google_service_account.deployer.email}"
}

resource "google_service_account_iam_member" "github_deploys" {
  for_each           = toset(var.github_repositories)
  service_account_id = google_service_account.deployer.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "principalSet://iam.googleapis.com/${google_iam_workload_identity_pool.github.name}/attribute.repository/${var.github_owner}/${each.value}"
}

# ------------------------------------------------------------------ the two people of the scenario
# The cloud scenario needs two identities (four eyes): service accounts stand in for the investigator and
# the approver. The deployer mints their ID tokens by impersonation; the services grant them roles
# (identity_subject_roles) and the assistant's invoker list names them.
resource "google_service_account" "scenario" {
  for_each     = toset(["investigator", "approver"])
  account_id   = "scenario-${each.value}"
  display_name = "Scenario ${each.value} (stands in for a person)"
}

resource "google_service_account_iam_member" "deployer_mints_tokens" {
  for_each           = google_service_account.scenario
  service_account_id = each.value.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:${google_service_account.deployer.email}"
}

# ------------------------------------------------------------------ a budget alert
resource "google_billing_budget" "alert" {
  count           = var.billing_account == "" ? 0 : 1
  billing_account = var.billing_account
  display_name    = "finance-ai landscape: anything above free"
  budget_filter {
    projects = ["projects/${data.google_project.this.number}"]
  }
  amount {
    specified_amount {
      currency_code = var.budget_currency
      units         = tostring(var.budget_amount)
    }
  }
  threshold_rules {
    threshold_percent = 0.01 # the first cent
  }
  threshold_rules {
    threshold_percent = 1.0
  }
}

# ------------------------------------------------------------------ the Gemini key (no value here)
resource "google_secret_manager_secret" "gemini_api_key" {
  secret_id = "gemini-api-key"
  labels    = local.labels
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

output "image_repository" {
  value = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.landscape.repository_id}"
}

output "state_bucket" {
  value = google_storage_bucket.state.name
}

output "workload_identity_provider" {
  description = "GitHub Actions: google-github-actions/auth's workload_identity_provider."
  value       = google_iam_workload_identity_pool_provider.github.name
}

output "deployer_service_account" {
  value = google_service_account.deployer.email
}

output "scenario_service_accounts" {
  description = "The two people of the cloud scenario: repository variables SCENARIO_INVESTIGATOR_SA and SCENARIO_APPROVER_SA."
  value       = { for k, v in google_service_account.scenario : k => v.email }
}

output "gemini_api_key_secret" {
  value = google_secret_manager_secret.gemini_api_key.secret_id
}
