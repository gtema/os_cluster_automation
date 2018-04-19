# os_cluster_automation

This repo provides a set of ansible playbooks for the OpenShift/K8 cluster creation, as an automation of the infrastructure creation for the [blueprint](https://opentelekomcloud.github.io/techblog/blueprints/2018-03-23-openshift-origin-fedora-atomic.html)

## Overview

The repo provides currently 4 standalone playbooks:

* VPC creation (playbooks/infra/vpc.yml)
* Bastion Host (jump) for the further access to the cluster environment (playbooks/infra/bastion.yml)
* DNS infrastructure (playbooks/infra/dns.yml)
* Cluster infra (playbooks/infra/app_cluster.yml)


## Usage

* First you need to adapt Ansible variables in the `group_vars/all.yml`. They are shared between all individual playbooks

It is also suggested to export variable CLUSTER_DOMAIN_NAME with the same value, as in `group_vars/all.yml`. This will help filter only the servers list from others

### VPC creation

After the global variables are adapted the following can be done for the VPC creation:

  `ansible-playbook -i inventory.py playbooks/infra/vpc.yml`

This command will create VPC (network, default subnetwork, router)

Note: due to the issue in shade library the SNAT is not enabled on the VPC. After the playbook is complete please enable it manually


### Bastion Host

The bastion (jump) host can be created with the following command:

  `ansible-playbook -i inventory.py playbooks/infra/vpc.yml`

This starts one server instance (ECS) and assigns floating IP to it. In addition openstackclient will be installed and `~/.config/openstack/{clouds,secure}.yaml` will be pushed from the local machine if found in regular places (`current_dir`, `~/.config/openstack`, `/etc/openstack`) or generated from environment (if not found - see `roles/bastion/tasks/os_config.yml`). This is required for some further steps, which should be executed from inside of the VPC.

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

  `ansible-playbook -i inventory -i inventory.py playbooks/infra/dns.yml`

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
  `ansible-playbook -i inventory -i inventory.py playbooks/infra/app_cluster.yml`

Register provided cluster nodes in the DNS (would be executed from bastion host):
  `ansible-playbook -i inventory -i inventory.py playbooks/infra/populate_cluster_dns.yml`


### Install Openshift

When the cluster is available the regular ansible installation of the OpenShift can be triggered. It should be noted, that the installation should be started from the host, which is able to resolve DNS names of instances and access them (i.e. curl). So it is either possible to do the installation from bastion server, inside app-cluster subnet, or if a VPN connection is established and the hosts are available (i.e. curl openshift.oc.DOMAIN_NAME)
