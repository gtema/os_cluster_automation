#!/usr/bin/env python
"""
This is an Ansible dynamic inventory for OpenStack.

It requires your OpenStack credentials to be set in clouds.yaml or your shell
environment.

The code is based on two works:
* https://raw.githubusercontent.com/ansible/ansible/devel/contrib/inventory/openstack.py
* https://github.com/openshift/openshift-ansible/blob/master/playbooks/openstack/inventory.py

"""

from __future__ import print_function

import argparse
import collections
import json
import os
import sys
import time
# from pathlib import Path

from distutils.version import StrictVersion

import os_client_config
import shade
import shade.inventory

CONFIG_FILES = ['/etc/ansible/openstack.yaml', '/etc/ansible/openstack.yml']

#
# def base_cluster_inventory(cluster_hosts):
#     '''Set the base cluster inventory.'''
#     inventory = {}
#     # print('hosts: %s' % cluster_hosts)
#
#     masters = [server.name for server in cluster_hosts
#                if server.metadata['host_type'] == 'master']
#
#     etcd = [server.name for server in cluster_hosts
#             if server.metadata['host_type'] == 'etcd']
#     if not etcd:
#         etcd = masters
#
#     infra_hosts = [server.name for server in cluster_hosts
#                    if server.metadata['host_type'] == 'node' and
#                    server.metadata['host_subtype'] == 'infra']
#
#     app = [server.name for server in cluster_hosts
#            if server.metadata['host_type'] == 'node' and
#            server.metadata['host_subtype'] == 'app']
#
#     # cns = [server.name for server in cluster_hosts
#     #        if server.metadata['host-type'] == 'cns']
#
#     nodes = list(set(masters + infra_hosts + app))
#
#     dns = [server.name for server in cluster_hosts
#            if server.metadata['host_type'] == 'dns']
#
#     load_balancers = [server.name for server in cluster_hosts
#                       if server.metadata['host_type'] == 'lb']
#
#     osev3 = list(set(nodes + etcd + load_balancers))
#
#     inventory['cluster_hosts'] = {'hosts': [s.name for s in cluster_hosts]}
#     inventory['OSEv3'] = {'hosts': osev3}
#     inventory['masters'] = {'hosts': masters}
#     inventory['etcd'] = {'hosts': etcd}
#     inventory['nodes'] = {'hosts': nodes}
#     inventory['infra_hosts'] = {'hosts': infra_hosts}
#     inventory['app'] = {'hosts': app}
#     # inventory['glusterfs'] = {'hosts': cns}
#     inventory['dns'] = {'hosts': dns}
#     # inventory['lb'] = {'hosts': load_balancers}
#     inventory['localhost'] = {'ansible_connection': 'local'}
#
#     return inventory
#
#
# def get_docker_storage_mountpoints(volumes):
#     '''Check volumes to see if they're being used for docker storage'''
#     docker_storage_mountpoints = {}
#     for volume in volumes:
#         if volume.metadata.get('purpose') == "openshift_docker_storage":
#             for attachment in volume.attachments:
#                 if attachment.server_id in docker_storage_mountpoints:
#                     docker_storage_mountpoints[attachment.server_id].append(attachment.device)
#                 else:
#                     docker_storage_mountpoints[attachment.server_id] = [attachment.device]
#     return docker_storage_mountpoints
#
#
# def _get_hostvars(server, docker_storage_mountpoints):
#     ssh_ip_address = server.public_v4 or server.private_v4
#     hostvars = {
#         'ansible_host': ssh_ip_address,
#         'ansible_hostname': server.name
#     }
#
#     metadata = server.metadata
#
#     public_v4 = server.public_v4 or server.private_v4
#     if public_v4:
#         hostvars['public_v4'] = server.public_v4
#         hostvars['openshift_public_ip'] = server.public_v4
#     # TODO(shadower): what about multiple networks?
#     if server.private_v4:
#         hostvars['private_v4'] = server.private_v4
#         hostvars['openshift_ip'] = server.private_v4
#
#         # NOTE(shadower): Yes, we set both hostname and IP to the private
#         # IP address for each node. OpenStack doesn't resolve nodes by
#         # name at all, so using a hostname here would require an internal
#         # DNS which would complicate the setup and potentially introduce
#         # performance issues.
#         hostvars['openshift_hostname'] = server.metadata.get(
#             'openshift_hostname', server.private_v4)
#     hostvars['openshift_public_hostname'] = server.name
#
#     # if server.metadata['host-type'] == 'cns':
#     #     hostvars['glusterfs_devices'] = ['/dev/nvme0n1']
#
#     node_labels = server.metadata.get('node_labels')
#     # NOTE(shadower): the node_labels value must be a dict not string
#     if node_labels and not isinstance(node_labels, Mapping):
#         node_labels = json.loads(node_labels)
#
#     if node_labels:
#         hostvars['openshift_node_labels'] = node_labels
#
#     # check for attached docker storage volumes
#     if 'os-extended-volumes:volumes_attached' in server:
#         if server.id in docker_storage_mountpoints:
#             hostvars['docker_storage_mountpoints'] = ' '.join(
#                 docker_storage_mountpoints[server.id])
#
#     if 'host_type' in metadata:
#         hostvars['host_type'] = metadata['host_type']
#     if 'host_subtype' in metadata:
#         hostvars['host_subtype'] = metadata['host_subtype']
#
#     return hostvars
#
#
# def build_inventory():
#     '''Build the dynamic inventory.'''
#     shade.simple_logging(debug=True)
#     cloud = shade.openstack_cloud()
#     with open('inv.log', 'a') as fh:
#         fh.write('env %s\n' % os.getenv('CLUSTER_STACK_NAME'))
#
#     inventory = {}
#     # # TODO(shadower): filter the servers based on the `OPENSHIFT_CLUSTER`
#     # # environment variable.
#     cluster_hosts = []
#     cluster_hosts = [
#         server for server in cloud.list_servers(filters={'name': 'goncharov.org'})
#         if 'metadata' in server and
#         (
#             ('cluster_id' in server.metadata)
#             or ('group' in server.metadata)
#         )
#     ]
#
#     inventory = base_cluster_inventory(cluster_hosts)
#
#     for server in cluster_hosts:
#         if 'group' in server.metadata:
#             group = server.metadata.get('group')
#             if group not in inventory:
#                 inventory[group] = {'hosts': []}
#             inventory[group]['hosts'].append(server.name)
#
#     inventory['_meta'] = {'hostvars': {}}
#     #
#     # # cinder volumes used for docker storage
#     # docker_storage_mountpoints = get_docker_storage_mountpoints(
#     #     cloud.list_volumes())
#     # for server in cluster_hosts:
#     #     inventory['_meta']['hostvars'][server.name] = _get_hostvars(
#     #         server,
#     #         docker_storage_mountpoints)
#
#     stout = _get_stack_outputs(cloud)
#     if stout is not None:
#         try:
#             print('stout is %s' % stout)
#             inventory['localhost'].update({
#                 'openshift_openstack_api_lb_provider':
#                 stout['api_lb_provider'],
#                 'openshift_openstack_api_lb_port_id':
#                 stout['api_lb_vip_port_id'],
#                 'openshift_openstack_api_lb_sg_id':
#                 stout['api_lb_sg_id']})
#         except KeyError:
#             pass  # Not an API load balanced deployment
#     #
#     #     try:
#     #         inventory['OSEv3']['vars'] = _get_kuryr_vars(cloud, stout)
#     #     except KeyError:
#     #         pass  # Not a kuryr deployment
#     return inventory
#
#
# def _get_stack_outputs(cloud_client):
#     """Returns a dictionary with the stack outputs"""
#     cluster_name = os.getenv('CLUSTER_STACK_NAME', 'ag-app-stack')
#
#     stack = cloud_client.get_stack(cluster_name)
#     if stack is None or stack['stack_status'] not in (
#             'CREATE_COMPLETE', 'UPDATE_COMPLETE'):
#         return None
#
#     data = {}
#     for output in stack['outputs']:
#         data[output['output_key']] = output['output_value']
#     return data

#
# def _get_kuryr_vars(cloud_client, data):
#     """Returns a dictionary of Kuryr variables resulting of heat stacking"""
#     settings = {}
#     settings['kuryr_openstack_pod_subnet_id'] = data['pod_subnet']
#     settings['kuryr_openstack_worker_nodes_subnet_id'] = data['vm_subnet']
#     settings['kuryr_openstack_service_subnet_id'] = data['service_subnet']
#     settings['kuryr_openstack_pod_sg_id'] = data['pod_access_sg_id']
#     settings['kuryr_openstack_pod_project_id'] = (
#         cloud_client.current_project_id)
#
#     settings['kuryr_openstack_auth_url'] = cloud_client.auth['auth_url']
#     settings['kuryr_openstack_username'] = cloud_client.auth['username']
#     settings['kuryr_openstack_password'] = cloud_client.auth['password']
#     if 'user_domain_id' in cloud_client.auth:
#         settings['kuryr_openstack_user_domain_name'] = (
#             cloud_client.auth['user_domain_id'])
#     else:
#         settings['kuryr_openstack_user_domain_name'] = (
#             cloud_client.auth['user_domain_name'])
#     # FIXME(apuimedo): consolidate kuryr controller credentials into the same
#     #                  vars the openstack playbook uses.
#     settings['kuryr_openstack_project_id'] = cloud_client.current_project_id
#     if 'project_domain_id' in cloud_client.auth:
#         settings['kuryr_openstack_project_domain_name'] = (
#             cloud_client.auth['project_domain_id'])
#     else:
#         settings['kuryr_openstack_project_domain_name'] = (
#             cloud_client.auth['project_domain_name'])
#     return settings



def get_groups_from_server(server_vars, namegroup=True):
    groups = []

    region = server_vars['region']
    cloud = server_vars['cloud']
    metadata = server_vars.get('metadata', {})
    host_type = metadata.get('host_type', '')
    host_subtype = metadata.get('host_subtype', '')
    if host_type == 'master':
        groups.append('masters')
        groups.append('nodes')
    if host_type == 'etcd':
        groups.append('etcd')
        groups.append('nodes')
    if host_type == 'node' and host_subtype == 'infra':
        groups.append('infra_hosts')
        groups.append('nodes')
    if host_type == 'node' and host_subtype == 'app':
        groups.append('app')
        groups.append('nodes')

    # # Create a group for the cloud
    # groups.append(cloud)
    #
    # # Create a group on region
    # groups.append(region)
    #
    # # And one by cloud_region
    # groups.append("%s_%s" % (cloud, region))

    # Check if group metadata key in servers' metadata
    if 'group' in metadata:
        groups.append(metadata['group'])

    # for extra_group in metadata.get('groups', '').split(','):
    #     if extra_group:
    #         groups.append(extra_group.strip())
    #
    # groups.append('instance-%s' % server_vars['id'])
    # if namegroup:
    #     groups.append(server_vars['name'])
    #
    # for key in ('flavor', 'image'):
    #     if 'name' in server_vars[key]:
    #         groups.append('%s-%s' % (key, server_vars[key]['name']))
    #
    # for key, value in iter(metadata.items()):
    #     groups.append('meta-%s_%s' % (key, value))
    #
    # az = server_vars.get('az', None)
    # if az:
    #     # Make groups for az, region_az and cloud_region_az
    #     groups.append(az)
    #     groups.append('%s_%s' % (region, az))
    #     groups.append('%s_%s_%s' % (cloud, region, az))
    return groups


def get_host_groups(inventory, refresh=False, cloud=None):
    (cache_file, cache_expiration_time) = get_cache_settings(cloud)
    if is_cache_stale(cache_file, cache_expiration_time, refresh=refresh):
        groups = to_json(get_host_groups_from_cloud(inventory))
        with open(cache_file, 'w') as f:
            f.write(groups)
    else:
        with open(cache_file, 'r') as f:
            groups = f.read()
    return groups


def append_hostvars(hostvars, groups, key, server, namegroup=False):
    hostvars[key] = dict(
        ansible_ssh_host=server['public_v4'] or server['private_v4'],
        ansible_host=server['name'],
        openstack=server)

    metadata = server.get('metadata', {})
    if 'ansible_user' in metadata:
        hostvars[key]['ansible_user'] = metadata['ansible_user']

    for group in get_groups_from_server(server, namegroup=namegroup):
        groups[group].append(key)


def get_host_groups_from_cloud(inventory):
    groups = collections.defaultdict(list)
    firstpass = collections.defaultdict(list)
    hostvars = {}
    list_args = {}
    if hasattr(inventory, 'extra_config'):
        use_hostnames = inventory.extra_config['use_hostnames']
        list_args['expand'] = inventory.extra_config['expand_hostvars']
        if StrictVersion(shade.__version__) >= StrictVersion("1.6.0"):
            list_args['fail_on_cloud_config'] = \
                inventory.extra_config['fail_on_errors']
    else:
        use_hostnames = False

    # Try to filter servers based on the CLUSTER_DOMAIN_NAME env
    cluster_domain_name = os.getenv('CLUSTER_DOMAIN_NAME', None)
    hosts = []

    if cluster_domain_name:
        hosts = [
            server for server in inventory.clouds[0].list_servers(
                filters={'name': cluster_domain_name})
            if 'metadata' in server and
            (
                ('cluster_id' in server.metadata)
                or ('group' in server.metadata)
            )
        ]
    else:
        hosts = inventory.list_hosts(**list_args)

    for server in hosts:

        if 'private_v4' not in server:
            continue
        firstpass[server['name']].append(server)
    for name, servers in firstpass.items():
        if len(servers) == 1 and use_hostnames:
            append_hostvars(hostvars, groups, name, servers[0])
        else:
            server_ids = set()
            # Trap for duplicate results
            for server in servers:
                server_ids.add(server['id'])
            if len(server_ids) == 1 and use_hostnames:
                append_hostvars(hostvars, groups, name, servers[0])
            else:
                for server in servers:
                    append_hostvars(
                        hostvars, groups, server['id'], server,
                        namegroup=True)
    groups['_meta'] = {'hostvars': hostvars}
    return groups


def is_cache_stale(cache_file, cache_expiration_time, refresh=False):
    ''' Determines if cache file has expired, or if it is still valid '''
    if refresh:
        return True
    if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0:
        mod_time = os.path.getmtime(cache_file)
        current_time = time.time()
        if (mod_time + cache_expiration_time) > current_time:
            return False
    return True


def get_cache_settings(cloud=None):
    config = os_client_config.config.OpenStackConfig(
        config_files=os_client_config.config.CONFIG_FILES + CONFIG_FILES)
    # For inventory-wide caching
    cache_expiration_time = config.get_cache_expiration_time()
    cache_path = config.get_cache_path()
    if cloud:
        cache_path = '{0}_{1}'.format(cache_path, cloud)
    if not os.path.exists(cache_path):
        os.makedirs(cache_path)
    cache_file = os.path.join(cache_path, 'ansible-inventory.cache')
    return (cache_file, cache_expiration_time)


def parse_args():
    parser = argparse.ArgumentParser(description='OpenStack Inventory Module')
    parser.add_argument('--cloud', default=os.environ.get('OS_CLOUD'),
                        help='Cloud name (default: None')
    parser.add_argument('--private',
                        action='store_true',
                        help='Use private address for ansible host')
    parser.add_argument('--refresh', action='store_true',
                        help='Refresh cached information')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug output')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--list', action='store_true',
                       help='List active servers')
    group.add_argument('--host', help='List details about the specific host')

    return parser.parse_args()


def to_json(in_dict):
    return json.dumps(in_dict, sort_keys=True, indent=2)


def main():
    args = parse_args()
    try:
        config_files = os_client_config.config.CONFIG_FILES + CONFIG_FILES
        shade.simple_logging(debug=args.debug)
        inventory_args = dict(
            refresh=args.refresh,
            config_files=config_files,
            private=args.private,
            cloud=args.cloud,
        )
        if hasattr(shade.inventory.OpenStackInventory, 'extra_config'):
            inventory_args.update(dict(
                config_key='ansible',
                config_defaults={
                    'use_hostnames': False,
                    'expand_hostvars': True,
                    'fail_on_errors': True,
                }
            ))

        inventory = shade.inventory.OpenStackInventory(**inventory_args)

        if args.list:
            output = get_host_groups(inventory, refresh=args.refresh, cloud=args.cloud)
        elif args.host:
            output = to_json(inventory.get_host(args.host))
        print(output)
    except shade.OpenStackCloudException as e:
        sys.stderr.write('%s\n' % e.message)
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()

# if __name__ == '__main__':
#     cache_file = '.ansible_inventory'
#     # my_file = Path(cache_file)
#     with open('inv.log', 'a') as fh:
#         import datetime
#         now = datetime.datetime.now()
#         fh.write('call at %s\n' % now)
#     if 0 and os.path.isfile(cache_file):
#         with open(cache_file, 'r') as fh:
#             print(fh.read())
#     else:
#         inv = json.dumps(build_inventory(), indent=4, sort_keys=True)
#         with(open(cache_file, 'w')) as fh:
#             fh.write(inv)
#         print(inv)
