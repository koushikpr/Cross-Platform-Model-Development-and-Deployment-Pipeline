provider "openstack" {
  user_name   = var.openstack_username
  password    = var.openstack_password
  auth_url    = var.openstack_auth_url
  tenant_name = var.openstack_tenant_name
  region      = var.openstack_region
}

# Variables
variable "openstack_username" {
  description = "OpenStack username"
  type        = string
}

variable "openstack_password" {
  description = "OpenStack password"
  type        = string
}

variable "openstack_auth_url" {
  description = "OpenStack authentication URL"
  type        = string
}

variable "openstack_tenant_name" {
  description = "OpenStack tenant name"
  type        = string
}

variable "openstack_region" {
  description = "OpenStack region"
  type        = string
}

variable "image_id" {
  description = "Image ID for the instance"
  type        = string
}

variable "flavor_id" {
  description = "Flavor ID for the instance (GPU)"
  type        = string
}

variable "network_id" {
  description = "Network ID where the instance will be deployed"
  type        = string
}

variable "key_name" {
  description = "Key pair name for SSH access"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID to attach to the instance"
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
  default     = "/home/ubuntu"
}

# Security Group (OpenStack equivalent of AWS Security Group)
resource "openstack_networking_secgroup_v2" "p3_sg" {
  name        = "p3-instance-security-group"
  description = "Allow all inbound and outbound traffic"

  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr        = "0.0.0.0/0"
  }

  egress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr        = "0.0.0.0/0"
  }
}

# OpenStack Instance with Ansible Setup
resource "openstack_compute_instance_v2" "p3_instance" {
  name            = "p3-instance"
  image_id        = var.image_id
  flavor_id       = var.flavor_id
  key_pair        = var.key_name
  security_groups = [openstack_networking_secgroup_v2.p3_sg.name]
  network {
    uuid = var.network_id
  }

  user_data = <<-EOF
    #!/bin/bash
    sudo apt-get update -y
    sudo apt-get install -y ansible awscli

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

# Output instance public IP
output "instance_public_ip" {
  value = openstack_compute_instance_v2.p3_instance.access_ip_v4
}

# Output security group ID
output "security_group_id" {
  value = openstack_networking_secgroup_v2.p3_sg.id
}
