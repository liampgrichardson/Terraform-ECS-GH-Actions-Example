# Define the provider
provider "aws" {
  region = var.aws_region
  default_tags {
    tags = var.global_tags
  }
}

# TF state bucket
terraform {
  backend "s3" {
    bucket = "my-tfstate-bucket-001" # Replace with your S3 bucket name
    key    = "terraform.tfstate"
    region = "eu-west-1"             # Replace with your AWS region
  }
}

# Reference the existing ECR repository
data "aws_ecr_repository" "existing_repository" {
  name = var.ecr_repository_name # Replace with the actual repository name
}

# VPC Creation
resource "aws_vpc" "my_vpc" {
  cidr_block = "10.0.0.0/16"
  enable_dns_support = true
  enable_dns_hostnames = true
}

resource "aws_subnet" "my_subnet" {
  vpc_id = aws_vpc.my_vpc.id
  cidr_block = "10.0.1.0/24"
}

# Security Group Creation
resource "aws_security_group" "my_security_group" {
  name_prefix = "my-security-group"
  ingress {
    from_port = 80
    to_port = 80
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ECS Cluster Creation
resource "aws_ecs_cluster" "my_cluster" {
  name = "my-cluster"
}

# ECS Task Definition Creation
resource "aws_ecs_task_definition" "my_task_definition" {
  family = "my-task-definition"
  container_definitions = jsonencode([
    {
      name = "my-container"
      image = "${data.aws_ecr_repository.existing_repository.repository_url}:latest"
      network_mode            = "bridge"
      memory                  = 512
      memory_reservation      = 256
      portMappings = [
        {
          containerPort = 80
          hostPort = 80
        }
      ]
    }
  ])
}

# ECS Service Creation
resource "aws_ecs_service" "my_service" {
  name = "my-service"
  cluster = aws_ecs_cluster.my_cluster.id
  task_definition = aws_ecs_task_definition.my_task_definition.arn
  desired_count = 1
  launch_type = "EC2"
}
