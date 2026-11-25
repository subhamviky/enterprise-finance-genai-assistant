# Plans the foundation against a mocked google provider: no project, no credentials.
mock_provider "google" {
  mock_data "google_project" {
    defaults = {
      number = "123456789012"
    }
  }
}

variables {
  project_id      = "demo-project"
  github_owner    = "demo-owner"
  billing_account = "000000-000000-000000"
}

run "one_repository_one_database_no_keys" {
  command = plan

  assert {
    condition     = google_artifact_registry_repository.landscape.repository_id == "landscape" && google_firestore_database.default.name == "(default)" && google_firestore_database.default.type == "FIRESTORE_NATIVE"
    error_message = "One image repository and the project's one free Firestore database, shared."
  }

  assert {
    condition     = google_iam_workload_identity_pool_provider.github.attribute_condition == "assertion.repository_owner == 'demo-owner'" && length(google_service_account_iam_member.github_deploys) == 4
    error_message = "Only the owner's four repositories may deploy, through OIDC (no JSON key)."
  }

  assert {
    condition     = google_storage_bucket.state.public_access_prevention == "enforced" && google_storage_bucket.state.uniform_bucket_level_access == true
    error_message = "The Terraform state is never public."
  }

  assert {
    condition     = length(google_billing_budget.alert) == 1 && google_billing_budget.alert[0].threshold_rules[0].threshold_percent == 0.01
    error_message = "A budget alert fires at the first cent."
  }

  assert {
    condition     = google_secret_manager_secret.gemini_api_key.secret_id == "gemini-api-key"
    error_message = "The Gemini key's secret exists, without a value in Terraform."
  }
}

run "only_free_regions" {
  command = plan

  variables {
    region = "asia-south1"
  }

  expect_failures = [var.region]
}
