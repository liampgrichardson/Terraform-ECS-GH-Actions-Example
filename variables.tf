# AWS Region
variable "aws_region" {
  description = "The AWS region to deploy resources in"
  type        = string
}

variable "ecr_repository_name" {
  description = "Name of the ECR repository"
  type        = string
}

# Global tags
variable "global_tags" {
  description = "A map of global tags to apply to all resources"
  type        = map(string)
}
