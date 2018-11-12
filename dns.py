import argparse
import copy
import logging
import openstack
import os
import sys
import yaml

logger = logging.getLogger(__name__)

CACHE_FILE_NAME = '.dns.cache'


def parse_args():
    parser = argparse.ArgumentParser(description='OpenStack Inventory Module')
    parser.add_argument('--cloud',
                        help='Cloud name (default: None)')
    parser.add_argument('--config', default='dns_config.yaml',
                        help='Configuration file')
    parser.add_argument('--mode', default='cloud',
                        help='Work mode. "cloud" = query cloud, '
                        '"cache" = get data from cache')
    parser.add_argument('--force', action='store_true', default=False,
                        help='Force sending update for all current records')
    parser.add_argument('--debug', action='store_true', default=False,
                        help='Enable debug output')

    return parser.parse_args()


def set_logging():
    # create console handler and set level to debug
    ch = logging.StreamHandler()

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)


def scan_existing_cloud(cloud, domain):
    """Look for servers in given cloud connection, sort them based on
    domain name (server name contains domain) and generate DNS records
    """
    records = []
    try:
        logger.debug('connecting to cloud %s' % cloud)
        conn = openstack.connect(cloud=cloud)
        filters = {
            'name': domain['zone']
        }
        servers = conn.list_servers(filters=filters)

        zone_details = {
            'zone': domain['zone'],
            'server': domain['server']
        }
        if 'server_type' in domain and \
                domain['server_type'] != 'designate':
            if 'key_algorithm' in domain:
                zone_details['key_algorithm'] = domain['key_algorithm']
            if 'key_name' in domain:
                zone_details['key_name'] = domain['key_name']
            if 'key_secret' in domain:
                zone_details['key_secret'] = domain['key_secret']

        for server in servers:
            server_name = server.name
            suffix = '.' + zone_details['zone']
            a_name = server_name if not server_name.endswith(suffix) or \
                len(suffix) == 0 else server_name[:-len(suffix)]

            rec = copy.deepcopy(zone_details)
            rec['record'] = a_name
            rec['value'] = server.private_v4
            rec['type'] = 'A'
            rec['state'] = 'present'

            records.append(rec)
    except openstack.exceptions.OpenStackCloudException as e:
        logger.error('%s\n' % e.message)
        sys.exit(1)

    return records


def _build_dict(seq, key):
    """Build named dict from list of records
    """
    return dict(
        (d[key], dict(d, index=index))
        for (index, d) in enumerate(seq)
    )


def build_update_records(current_records, old_records, force=False):
    """Walk through the current records (for existing servers) and cached
    data (old records) and identify changes for update
    """
    update_records = []

    current_records_by_name = _build_dict(current_records, key='record')
    old_records_by_name = _build_dict(old_records, key='record')

    for old_rec in old_records_by_name:
        rec = old_records_by_name[old_rec]
        current_rec = current_records_by_name.pop(old_rec, None)
        if current_rec:
            if force or current_rec['value'] != rec['value']:
                # changed record
                update_records.append(current_rec)
            else:
                # unchanged record
                logger.debug('record %s should be alredy present, skipping' %
                             current_rec)
        else:
            # deleted record
            rec['state'] = 'absent'
            update_records.append(rec)

    for curr_rec in current_records_by_name:
        # remaining records are new
        update_records.append(current_records_by_name[curr_rec])

    return update_records


def main():
    args = parse_args()
    with open(args.config) as yamlcfg:
        cfg = yaml.load(yamlcfg)
    if args.debug or cfg['loglevel'].lower() == 'debug':
        logger.setLevel(logging.DEBUG)

    domain = cfg['domain']
    cloud = args.cloud if args.cloud else cfg['cloud']
    if not cloud:
        cloud = os.environ.get('OS_CLOUD')
        # logger.error('cloud name is not given')
        # sys.exit(1)
    current_records = []
    cache_records = []

    # read cache (previous state)
    if os.path.exists(CACHE_FILE_NAME):
        with open(CACHE_FILE_NAME, 'r') as cache_file:
            cache_records = yaml.load(cache_file)
        if not cache_records or not isinstance(cache_records, (list, tuple)):
            logger.warning('Can not properly parse cache file')
            cache_records = []
    else:
        logger.warning('Previous DNS state is not known, existing records '
                       'will not be handled by the script')

    current_records = scan_existing_cloud(cloud, domain)

    update_records = build_update_records(
        current_records, cache_records, args.force
    )

    for rec in update_records:
        logger.debug('DNS record: %s' % rec)

    with open(CACHE_FILE_NAME, 'w') as cache_file:
        yaml.dump(current_records, cache_file, default_flow_style=False)

    sys.exit(0)


if __name__ == '__main__':
    set_logging()

    main()
