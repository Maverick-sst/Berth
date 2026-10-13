variable "aws_region" {
  description = "AWS region for the Berth cluster"
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "EKS cluster name"
  type        = string
  default     = "berth-eks"
}

variable "environment" {
  description = "Environment tag applied to resources"
  type        = string
  default     = "dev"
}
