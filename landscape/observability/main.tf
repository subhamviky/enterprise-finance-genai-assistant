# Service level objectives and burn-rate alerts for the landscape's Cloud Run services (GCP-02 Phase B, item 8).
#
# Free tier: the SLOs read Cloud Run's own metrics (request count, request latency), which are not charged; an SLO has
# no price of its own. No log-based metrics here. The alerting charge in Google's tables starts on 1 September 2027,
# after this trial; alert policies are created without a notification channel unless one is given, so nothing is sent
# and nothing is paid by default. Applied by hand after the five services exist; it only reads them.
#
#   availability  the share of requests that are not server errors, over 28 days
#   latency       the share of requests answered within a threshold, over 28 days (the services whose path has no model)
#
# Each SLO gets one fast-burn alert: the error budget is being spent 10 times faster than the objective allows,
# measured over the last hour (the usual page-worthy rate).

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

variable "project_id" {
  type = string
}

variable "region" {
  type    = string
  default = "us-central1"
}

variable "availability_services" {
  type        = list(string)
  description = "Cloud Run services that get an availability SLO."
  default     = ["settlement-service", "reconciliation-service", "audit-ai-service", "o2c-agent-service-dev", "genai-assistant-service"]
}

variable "latency_services" {
  type        = map(number)
  description = "Cloud Run services that get a latency SLO (the non-model path) and the threshold in milliseconds. The assistant is left out: its answer waits for a language model."
  default     = { "settlement-service" = 1000, "reconciliation-service" = 1000 }
}

variable "availability_goal" {
  type    = number
  default = 0.99
}

variable "latency_goal" {
  type    = number
  default = 0.95
}

variable "notification_channels" {
  type        = list(string)
  description = "Existing notification channel ids to send the alerts to; empty means the alerts are visible in the console only."
  default     = []
}

locals {
  filter_base = "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\""
  labels      = { landscape = "finance-ai", managed-by = "terraform" }
  services    = toset(concat(var.availability_services, keys(var.latency_services)))
}

resource "google_monitoring_custom_service" "run" {
  for_each     = local.services
  service_id   = "cr-${each.key}"
  display_name = "${each.key} (Cloud Run)"
  user_labels  = local.labels
}

resource "google_monitoring_slo" "availability" {
  for_each            = toset(var.availability_services)
  service             = google_monitoring_custom_service.run[each.key].service_id
  slo_id              = "availability"
  display_name        = "${each.key}: ${var.availability_goal * 100}% of requests are not server errors"
  goal                = var.availability_goal
  rolling_period_days = 28

  request_based_sli {
    good_total_ratio {
      good_service_filter  = join(" ", [local.filter_base, "resource.label.service_name=\"${each.key}\"", "metric.label.response_code_class!=\"5xx\""])
      total_service_filter = join(" ", [local.filter_base, "resource.label.service_name=\"${each.key}\""])
    }
  }
}

resource "google_monitoring_slo" "latency" {
  for_each            = var.latency_services
  service             = google_monitoring_custom_service.run[each.key].service_id
  slo_id              = "latency"
  display_name        = "${each.key}: ${var.latency_goal * 100}% of requests answered within ${each.value} ms"
  goal                = var.latency_goal
  rolling_period_days = 28

  request_based_sli {
    distribution_cut {
      distribution_filter = join(" ", ["metric.type=\"run.googleapis.com/request_latencies\"", "resource.type=\"cloud_run_revision\"", "resource.label.service_name=\"${each.key}\""])
      range {
        max = each.value
      }
    }
  }
}

resource "google_monitoring_alert_policy" "availability_burn" {
  for_each     = google_monitoring_slo.availability
  display_name = "${each.key} availability: fast burn of the error budget"
  combiner     = "OR"
  user_labels  = local.labels

  conditions {
    display_name = "error budget burning 10 times too fast over 1 hour"
    condition_threshold {
      filter          = "select_slo_burn_rate(\"${each.value.name}\", \"1h\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "0s"
    }
  }

  notification_channels = var.notification_channels
}

resource "google_monitoring_alert_policy" "latency_burn" {
  for_each     = google_monitoring_slo.latency
  display_name = "${each.key} latency: fast burn of the error budget"
  combiner     = "OR"
  user_labels  = local.labels

  conditions {
    display_name = "error budget burning 10 times too fast over 1 hour"
    condition_threshold {
      filter          = "select_slo_burn_rate(\"${each.value.name}\", \"1h\")"
      comparison      = "COMPARISON_GT"
      threshold_value = 10
      duration        = "0s"
    }
  }

  notification_channels = var.notification_channels
}

output "slos" {
  value = merge(
    { for k, v in google_monitoring_slo.availability : "${k}/availability" => v.goal },
    { for k, v in google_monitoring_slo.latency : "${k}/latency" => v.goal },
  )
}
