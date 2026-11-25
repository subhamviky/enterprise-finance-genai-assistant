variable "project_id" {
  type        = string
  description = "The landscape's Google Cloud project (deploy/gcp/landscape.vars)."
}

variable "region" {
  type    = string
  default = "us-central1"

  validation {
    condition     = contains(["us-west1", "us-central1", "us-east1"], var.region)
    error_message = "Always Free regions only: us-west1, us-central1, us-east1."
  }
}

variable "github_owner" {
  type        = string
  description = "The GitHub account that owns the repositories allowed to deploy."
}

variable "github_repositories" {
  type        = list(string)
  description = "The repositories (names, without the owner) whose Actions may deploy."
  default = ["enterprise-finance-genai-assistant", "financial-settlement-platform", "payment-reconciliation-engine",
  "order-to-cash-agentic-ai"]
}

variable "images_kept" {
  type        = number
  description = "Versions kept per image (the free tier stores 0.5 GB)."
  default     = 2
}

variable "billing_account" {
  type        = string
  description = "The billing account id for the budget alert (empty: no alert)."
  default     = ""
}

variable "budget_amount" {
  type    = number
  default = 1
}

variable "budget_currency" {
  type    = string
  default = "USD"
}
