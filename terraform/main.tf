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
  name = var.ecr_repository_name # variable is received by gh actions workflow
}

# Cognito User Pool
resource "aws_cognito_user_pool" "my_user_pool" {
  name = "my-user-pool"
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "my_user_pool_client" {
  name         = "my-user-pool-client"
  user_pool_id = aws_cognito_user_pool.my_user_pool.id
  generate_secret = false
  allowed_oauth_flows = ["code"]
  allowed_oauth_scopes = ["openid"]
  callback_urls = ["http://${aws_lb.my_alb.dns_name}/oauth2/idpresponse"]
}

# Cognito User
resource "aws_cognito_user" "admin_user" {
  user_pool_id = aws_cognito_user_pool.my_user_pool.id
  username     = var.cognito_username
  password     = var.cognito_password
  force_alias_creation = true
}

# ACM SSL Certificate for ALB
resource "aws_acm_certificate" "my_cert" {
  domain_name       = aws_lb.my_alb.dns_name
  validation_method = "DNS"  # Use DNS validation
}

# ALB Listener with SSL (HTTPS) and Cognito Authentication
resource "aws_lb_listener" "https_listener" {
  load_balancer_arn = aws_lb.my_alb.arn
  port              = 443
  protocol          = "HTTPS"

  ssl_policy = "ELBSecurityPolicy-2016-08"  # You can specify a different SSL policy here if needed

  default_action {
    type = "authenticate-cognito"
    authenticate_cognito {
      user_pool_arn       = aws_cognito_user_pool.my_user_pool.arn
      user_pool_client_id = aws_cognito_user_pool_client.my_user_pool_client.id
      user_pool_domain    = aws_cognito_user_pool.my_user_pool.id
      session_cookie_name = "AWSELBAuthSessionCookie"
      scope               = "openid"
      on_unauthenticated_request = "authenticate"
    }
  }

  # Forward action if authenticated
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.my_target_group.arn
  }

  # Attach the ACM certificate ARN for SSL termination
  certificate_arn = aws_acm_certificate.my_cert.arn
}

# VPC Creation
resource "aws_vpc" "my_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
}

# Subnet Creation
resource "aws_subnet" "my_subnet" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "eu-west-1a" # Specify AZ
}

# Additional Subnet in a different AZ
resource "aws_subnet" "my_subnet_2" {
  vpc_id                  = aws_vpc.my_vpc.id
  cidr_block              = "10.0.2.0/24"
  availability_zone       = "eu-west-1b" # Specify another AZ
}

# Internet Gateway
resource "aws_internet_gateway" "my_igw" {
  vpc_id = aws_vpc.my_vpc.id
}

# Route Table for Public Subnet
resource "aws_route_table" "my_route_table" {
  vpc_id = aws_vpc.my_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.my_igw.id
  }
}

# Associate Route Table with Subnet 1
resource "aws_route_table_association" "my_rta" {
  subnet_id      = aws_subnet.my_subnet.id
  route_table_id = aws_route_table.my_route_table.id
}

# Associate Route Table with Subnet 2
resource "aws_route_table_association" "my_rta_2" {
  subnet_id      = aws_subnet.my_subnet_2.id
  route_table_id = aws_route_table.my_route_table.id
}

# Security Group Creation for ALB
resource "aws_security_group" "alb_security_group" {
  name_prefix = "alb-security-group"
  vpc_id      = aws_vpc.my_vpc.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Security Group Creation for ECS
resource "aws_security_group" "my_security_group" {
  name_prefix = "ecs-security-group"
  vpc_id      = aws_vpc.my_vpc.id

  ingress {
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_security_group.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Application Load Balancer
resource "aws_lb" "my_alb" {
  name               = "Trading-Application-ALB"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_security_group.id]
  subnets            = [aws_subnet.my_subnet.id, aws_subnet.my_subnet_2.id]
}

# ALB Target Group
resource "aws_lb_target_group" "my_target_group" {
  name       = "my-target-group"
  port       = 80
  protocol   = "HTTP"
  vpc_id     = aws_vpc.my_vpc.id
  target_type = "ip" # Required for Fargate tasks
}

# ECS Cluster Creation
resource "aws_ecs_cluster" "my_cluster" {
  name = "my-cluster"
}

# ECS Task Execution Role
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecsTaskExecutionRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Effect    = "Allow"
    }]
  })
}

# ECS Task Role
resource "aws_iam_role" "ecs_task_role" {
  name = "ecsTaskRole"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Effect    = "Allow"
    }]
  })
}

# ECS Task Role (updated to include Timestream policy)
resource "aws_iam_policy" "ecs_timestream_policy" {
  name        = "ecsTimestreamPolicy"
  description = "Policy to allow ECS tasks to interact with Timestream"
  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Sid       = "AllowTimestreamReadAccess",
        Effect    = "Allow",
        Action    = [
          "timestream:DescribeEndpoints",
          "timestream:Select",
          "timestream:Query",
          "timestream:SelectValues",
          "timestream:DescribeTable",
          "timestream:ListMeasures"
        ],
        Resource  = "*"
      }
    ]
  })
}

# Attach the Timestream policy to the ECS Task Role
resource "aws_iam_role_policy_attachment" "ecs_timestream_policy_attachment" {
  role       = aws_iam_role.ecs_task_role.name
  policy_arn = aws_iam_policy.ecs_timestream_policy.arn
}

# Add permissions for task execution
resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Add permissions for CloudWatch logging
resource "aws_iam_role_policy_attachment" "ecs_cw_logging_policy_attachment" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess"
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "ecs_log_group" {
  name              = "/ecs/my-service"
  retention_in_days = 7 # Adjust retention as needed
}

# ECS Task Definition Creation
resource "aws_ecs_task_definition" "my_task_definition" {
  family                   = "my-task-definition"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn
  cpu                      = "256" # Specify CPU for Fargate
  memory                   = "512" # Specify Memory for Fargate

  container_definitions = jsonencode([
    {
      name      = "my-container"
      image     = "${data.aws_ecr_repository.existing_repository.repository_url}:${var.image_tag}"  # Use the image tag here
      cpu       = 256
      memory    = 512
      essential = true
      portMappings = [
        {
          containerPort = 80
          hostPort      = 80
          protocol      = "tcp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.ecs_log_group.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])
}

# ECS Service Creation
resource "aws_ecs_service" "my_service" {
  name            = "my-service"
  cluster         = aws_ecs_cluster.my_cluster.id
  task_definition = aws_ecs_task_definition.my_task_definition.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  force_new_deployment = true # Ensures new tasks use the updated image

  network_configuration {
    subnets         = [aws_subnet.my_subnet.id, aws_subnet.my_subnet_2.id]
    security_groups = [aws_security_group.my_security_group.id]
    assign_public_ip = true  # can be false because alb handles traffic
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.my_target_group.arn
    container_name   = "my-container"
    container_port   = 80
  }
}

# Output the ALB DNS Name
output "application_url" {
  description = "The URL to access the deployed application"
  value       = aws_lb.my_alb.dns_name
}

# Output image tag
output "image_tag" {
  description = "The image tag for the deployed application"
  value       = var.image_tag
  sensitive   = true
}
