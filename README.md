# os_cluster_automation

This repo provides a set of ansible playbooks for the OpenShift/K8 cluster creation, as an automation of the infrastructure creation for the [blueprint](https://opentelekomcloud.github.io/techblog/blueprints/2018-03-23-openshift-origin-fedora-atomic.html)

## Overview

The repo provides currently 4 standalone playbooks:

* VPC creation (playbooks/infra/main.yml)
* Bastion Host (jump) for the further access to the cluster environment (playbooks/bastion/main.yml)
* DNS infrastructure (playbooks/dns/main.yml)
* Cluster infra (playbooks/app_cluster/main.yml)

## Usage

* First you need to adapt Ansible variables in the `inventory/production/group_vars/all.yml`. They are shared between all individual playbooks


### VPC creation

After the global variables are adapted the following can be done for the VPC creation:

  `ansible-playbook -i inventory/production playbooks/infra/main.yaml`

This command will create VPC (network, default subnetwork, router)

Note: due to the issue in shade library the SNAT is not enabled on the VPC. After the playbook is complete please enable it manually


### Bastion Host

The bastion (jump) host can be created with the following command:

  `ansible-playbook -i inventory/production playbooks/bastion/main.yaml`

This starts one server instance (ECS) and assigns floating IP to it.

After this is done and the public IP is known the SSH configuration can be extended to access cloud through this host:

Assuming Public IP is 1.1.1.1, in the `./ssh/config` please add the following:

~~~~
# Bastion host
Host otc-bastion
  HostName 1.1.1.1
  User linux
  IdentityFile ~/.ssh/my-KeyPair.pem
  ControlMaster auto
  ControlPersist 5m

# App-cluster nodes access
Host 192.168.99.*
  ProxyCommand ssh -W %h:%p otc-bastion
  IdentityFile ~/.ssh/my-KeyPair.pem
  Port 22

# DNS servers
Host 192.168.178.*
  ProxyCommand ssh -W %h:%p otc-bastion
  IdentityFile ~/.ssh/my-KeyPair.pem    
~~~~


### DNS

Kubernetes and Openshift absolutely require proper naming resolution for each node in the cluster. To achieve this a local DNS servers (forward with own zone) are created:

  `ansible-playbook -i inventory/production playbooks/dns/main.yaml`

This will create one Master and configured in the variables amount of slaves and deploy private zone (name configured in vars). It also include own network with separated CIDR (192.168.178.0/24 in the example) and relative SecurityGroup. It is managed through the Heat stack


### App-cluster

The Openshift/K8 cluster includes (managed through the Heat stack):
* network with CIDR (192.168.99.0/24 in example)
* required security groups
* configured amount of master nodes
* configured amount of pod nodes (executors)
* configured amount of infra (openshift router) nodes
* additional volumes for the nodes

**Issue Heat:** If Heat uses block_device_mapping_v2 device names MUST be **vdX**. If **sdX** names are used stack will fail with not released port, making impossible to delete security groups and network (router interface can be deleted)

Provision the cluster:
  `ansible-playbook -i inventory/production playbooks/app_cluster/main.yaml`

Register provided cluster nodes in the DNS (would be executed from bastion host):
  `ansible-playbook -i inventory/production playbooks/app_cluster/populate_cluster_dns.yaml`


### Install Openshift

When the cluster is available the regular ansible installation of the OpenShift can be triggered. It should be noted, that the installation should be started from the host, which is able to resolve DNS names of instances and access them (i.e. curl). So it is either possible to do the installation from bastion server (after DNS servers are substituted), inside app-cluster subnet, or if a VPN connection is established and the hosts are available (i.e. curl openshift.oc.DOMAIN_NAME)
