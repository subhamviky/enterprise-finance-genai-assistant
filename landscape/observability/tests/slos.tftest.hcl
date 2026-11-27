mock_provider "google" {}

variables {
  project_id = "p"
}

run "an_availability_slo_per_service_and_a_latency_slo_for_the_non_model_path" {
  command = plan
  assert {
    condition     = length(google_monitoring_slo.availability) == 5
    error_message = "one availability SLO for each of the five services"
  }
  assert {
    condition     = toset(keys(google_monitoring_slo.latency)) == toset(["reconciliation-service", "settlement-service"])
    error_message = "latency SLOs only where no model is in the path"
  }
  assert {
    condition     = !contains(keys(google_monitoring_slo.latency), "genai-assistant-service")
    error_message = "the assistant's latency depends on a language model and has no latency SLO"
  }
}

run "every_slo_has_a_fast_burn_alert_and_no_channel_by_default" {
  command = plan
  assert {
    condition     = length(google_monitoring_alert_policy.availability_burn) == 5 && length(google_monitoring_alert_policy.latency_burn) == 2
    error_message = "one burn-rate alert per SLO"
  }
  assert {
    condition     = length(google_monitoring_alert_policy.availability_burn["settlement-service"].notification_channels) == 0
    error_message = "no notification channel unless one is given"
  }
}
