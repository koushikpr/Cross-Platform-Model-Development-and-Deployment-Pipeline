provider "aws" {
  region     = var.aws_region
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
}

# Variables
variable "aws_region" {
  description = "AWS region to deploy the instance"
  type        = string
  default = "us-east-2"
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
  default = "ami-058a8a5ab36292159"
}

variable "instance_type" {
  description = "Instance type to launch"
  type        = string
  default     = "t2.micro"
}

variable "vpc_id" {
  description = "VPC ID for the instance"
  type        = string
  default = "vpc-04a8cb127ef04a992"
}



variable "key_name" {
  description = "Key pair name for SSH access"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM instance profile that grants necessary permissions"
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
  vpc_security_group_ids = [aws_security_group.p3_sg.id]
  iam_instance_profile   = var.iam_instance_profile

  user_data = <<-EOF
    #!/bin/bash
    sudo yum update -y
    sudo yum install -y ansible aws-cli
    sudo yum install -y git
    # Create Ansible Directory
    mkdir -p ${var.home_dir}/ansible
    cd ${var.home_dir}/ansible


    # Fetch Ansible Playbook from Git
    git clone https://github.com/koushikpr/Cross-Platform-Model-Development-and-Deployment-Pipeline

    cd Cross-Platform-Model-Development-and-Deployment-Pipeline

    

    

    echo "Installing Jupyter-Notebook"

    ansible-playbook ansible/configurations/ec2/jupyter-setup.yml

    
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
