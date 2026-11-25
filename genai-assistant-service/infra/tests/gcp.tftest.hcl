# Plans the assistant's stack against a mocked google provider: no project, no credentials.
mock_provider "google" {}

variables {
  project_id = "demo-project"
}

run "free_tier_and_private" {
  command = plan

  variables {
    invoker_members        = ["user:ana@example.com"]
    identity_subject_roles = { "ana@example.com" = ["tenant:acme", "investigator"] }
  }

  assert {
    condition     = google_cloud_run_v2_service.app.template[0].scaling[0].min_instance_count == 0 && google_cloud_run_v2_service.app.template[0].scaling[0].max_instance_count == 1 && google_cloud_run_v2_service.app.template[0].containers[0].resources[0].cpu_idle == true
    error_message = "Scale to zero, one instance, CPU only during requests."
  }

  assert {
    condition = alltrue([for want in [
      "GENAI_STATE_BACKEND=firestore", "E2A_IDENTITY_SOURCE=gcp_cloud_run", "E2A_WORKLOAD_IDENTITY=gcp_id_token",
      "E2A_PROVIDER_PROFILE=simulated", "FIRESTORE_DATABASE=(default)",
    ] : contains([for e in google_cloud_run_v2_service.app.template[0].containers[0].env : "${e.name}=${e.value != null ? e.value : ""}"], want)])
    error_message = "State in the shared Firestore database, Cloud Run identity in and out, the simulated model by default."
  }

  assert {
    condition     = length(google_cloud_run_v2_service_iam_member.invokers) == 1 && length(google_secret_manager_secret_iam_member.gemini_key) == 0
    error_message = "Only the listed people invoke it; no key without the gemini_api profile."
  }
}

run "gemini_key_from_secret_manager" {
  command = plan

  variables {
    llm_profile           = "gemini_api"
    gemini_api_key_secret = "gemini-api-key"
  }

  assert {
    condition     = length([for e in google_cloud_run_v2_service.app.template[0].containers[0].env : e if e.name == "GEMINI_API_KEY" && e.value == null]) == 1 && length(google_secret_manager_secret_iam_member.gemini_key) == 1
    error_message = "The key is a Secret Manager reference, never a value."
  }
}

run "never_public" {
  command = plan

  variables {
    invoker_members = ["allUsers"]
  }

  expect_failures = [var.invoker_members]
}

run "only_free_models_and_regions" {
  command = plan

  variables {
    llm_profile = "google_vertex"
    region      = "europe-west1"
  }

  expect_failures = [var.llm_profile, var.region]
}
