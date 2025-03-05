provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

# Variables
variable "aws_region" {
  description = "AWS region to deploy the instance"
  type        = string
}

variable "aws_access_key" {
  description = "AWS access key from environment variable"
  type        = string
  default     = ""
}

variable "aws_secret_key" {
  description = "AWS secret key from environment variable"
  type        = string
  default     = ""
}

variable "ami_id" {
  description = "AMI ID for the instance"
  type        = string
}

variable "instance_type" {
  description = "Instance type to launch"
  type        = string
  default     = "p3.2xlarge"
}

variable "vpc_id" {
  description = "VPC ID for the instance"
  type        = string
}

variable "subnet_id" {
  description = "Subnet ID where the instance will be deployed"
  type        = string
}

variable "key_name" {
  description = "Key pair name for SSH access"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM instance profile that grants necessary permissions"
  type        = string
}

variable "ansible_s3_bucket" {
  description = "S3 bucket containing the Ansible playbook"
  type        = string
}

variable "ansible_playbook" {
  description = "Ansible playbook filename (e.g., setup.yml)"
  type        = string
}

variable "home_dir" {
  description = "Home directory of the default user"
  type        = string
  default     = "/home/ec2-user"
}

# Security Group
resource "aws_security_group" "p3_sg" {
  name        = "p3-instance-security-group"
  description = "Allow all inbound and outbound traffic"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# EC2 Instance with IAM Instance Profile & Ansible Setup
resource "aws_instance" "p3_instance" {
  ami                    = var.ami_id
  instance_type          = var.instance_type
  key_name               = var.key_name
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [aws_security_group.p3_sg.id]
  iam_instance_profile   = var.iam_instance_profile

  user_data = <<-EOF
    #!/bin/bash
    sudo yum update -y
    sudo yum install -y ansible aws-cli

    # Create Ansible Directory
    mkdir -p ${var.home_dir}/ansible
    cd ${var.home_dir}/ansible

    # Fetch Ansible Playbook from S3
    aws s3 cp s3://${var.ansible_s3_bucket}/${var.ansible_playbook} ${var.home_dir}/ansible/

    # Run the Playbook
    ansible-playbook ${var.ansible_playbook}
  EOF

  tags = {
    Name = "p3-instance"
  }
}

# Outputs
output "instance_public_ip" {
  value = aws_instance.p3_instance.public_ip
}

output "security_group_id" {
  value = aws_security_group.p3_sg.id
}
