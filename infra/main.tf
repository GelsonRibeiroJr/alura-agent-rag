terraform {
  required_version = ">= 1.0.0"
  required_providers {
    oci = {
      source  = "oracle/oci"
      version = ">= 5.0.0"
    }
  }
}

provider "oci" {
  region = "sa-saopaulo-1"
}

data "oci_identity_tenancy" "tenancy" {
  tenancy_id = "ocid1.tenancy.oc1..aaaaaaaaouwhkhedoftxp4togx3c5f6mbs3cwghqgo43h3et5xl6rieg5uzq"
}

data "oci_core_images" "ubuntu_amd" {
  compartment_id           = data.oci_identity_tenancy.tenancy.tenancy_id
  operating_system         = "Canonical Ubuntu"
  operating_system_version = "22.04"
  shape                    = "VM.Standard.E2.1.Micro"
  sort_by                  = "TIMECREATED"
  sort_order               = "DESC"
}

data "oci_identity_availability_domains" "ads" {
  compartment_id = data.oci_identity_tenancy.tenancy.tenancy_id
}

resource "oci_core_vcn" "nasa_vcn" {
  compartment_id = data.oci_identity_tenancy.tenancy.tenancy_id
  cidr_blocks    = ["10.0.0.0/16"]
  display_name   = "nasa-agente-vcn"
  dns_label      = "nasavcn"
}

resource "oci_core_internet_gateway" "nasa_ig" {
  compartment_id = data.oci_identity_tenancy.tenancy.tenancy_id
  vcn_id         = oci_core_vcn.nasa_vcn.id
  display_name   = "nasa-agente-ig"
}

resource "oci_core_route_table" "nasa_rt" {
  compartment_id = data.oci_identity_tenancy.tenancy.tenancy_id
  vcn_id         = oci_core_vcn.nasa_vcn.id
  display_name   = "nasa-agente-rt"

  route_rules {
    destination       = "0.0.0.0/0"
    destination_type  = "CIDR_BLOCK"
    network_entity_id = oci_core_internet_gateway.nasa_ig.id
  }
}

resource "oci_core_security_list" "nasa_sl" {
  compartment_id = data.oci_identity_tenancy.tenancy.tenancy_id
  vcn_id         = oci_core_vcn.nasa_vcn.id
  display_name   = "nasa-agente-sl"

  egress_security_rules {
    destination = "0.0.0.0/0"
    protocol    = "all"
  }

  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 8501
      max = 8501
    }
  }

  ingress_security_rules {
    protocol  = "6"
    source    = "0.0.0.0/0"
    stateless = false
    tcp_options {
      min = 22
      max = 22
    }
  }
}

resource "oci_core_subnet" "nasa_subnet" {
  compartment_id    = data.oci_identity_tenancy.tenancy.tenancy_id
  vcn_id            = oci_core_vcn.nasa_vcn.id
  cidr_block        = "10.0.1.0/24"
  display_name      = "nasa-agente-subnet-publica"
  dns_label         = "nasasubnet"
  route_table_id    = oci_core_route_table.nasa_rt.id
  security_list_ids = [oci_core_security_list.nasa_sl.id]
}

resource "oci_core_instance" "nasa_vm" {
  availability_domain = data.oci_identity_availability_domains.ads.availability_domains[0].name
  compartment_id      = data.oci_identity_tenancy.tenancy.tenancy_id
  display_name        = "nasa-agente-vm"
  shape               = "VM.Standard.E2.1.Micro"

  create_vnic_details {
    subnet_id        = oci_core_subnet.nasa_subnet.id
    assign_public_ip = true
    display_name     = "nasa-vm-vnic"
  }

  source_details {
    source_type = "image"
    source_id   = data.oci_core_images.ubuntu_amd.images[0].id
  }

  metadata = {
    ssh_authorized_keys = file("~/.ssh/id_rsa.pub")
    user_data = base64encode(<<-EOF
      #!/bin/bash
      exec > /var/log/user-data.log 2>&1
      
      fallocate -l 2G /swapfile
      chmod 600 /swapfile
      mkswap /swapfile
      swapon /swapfile
      echo '/swapfile none swap sw 0 0' >> /etc/fstab

      apt-get update
      apt-get install -y docker.io git
      systemctl start docker
      systemctl enable docker

      iptables -I INPUT -p tcp --dport 8501 -j ACCEPT

      cd /home/ubuntu
      git clone https://github.com/GelsonRibeiroJr/alura-agent-rag.git
      cd alura-agent-rag
      docker build -t app-nasa:v1 .
      docker run -d -p 8501:8501 --restart always --name nasa-agent app-nasa:v1
    EOF
    )
  }
}

output "url_agente_nasa" {
  value = "http://${oci_core_instance.nasa_vm.public_ip}:8501"
}