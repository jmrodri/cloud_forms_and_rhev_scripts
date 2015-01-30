#! /usr/bin/env python

####
##  Proof of concept to show how we can use oVirt REST APIs to
##  Launch a CFME appliance after we've imported it to oVirt as a VM Template.
####

import os
import sys
import time

try:
    from ovirtsdk.api import API
    from ovirtsdk.xml import params
    from ovirtsdk.infrastructure.errors import RequestError
except:
    print "Please re-run after you have installed 'ovirt-engine-sdk-python'"
    print "Example: easy_install ovirt-engine-sdk-python"
    sys.exit()

try:
    from paramiko import AutoAddPolicy
    from paramiko.client import SSHClient
except:
    print "Please re-run after you have installed 'paramiko'"
    print "Example: easy_install paramiko"
    sys.exit()
 

ENV_IP = "OVIRT_IP"
ENV_USERNAME = "OVIRT_USERNAME"
ENV_PASSWORD = "OVIRT_PASSWORD"
MB = 1024*1024
GB = 1024*MB

def create_vm_from_template(api, vm_name, cluster, template):
    vm_params = params.VM(name=vm_name, cluster=cluster, template=template)
    return api.vms.add(vm_params)

def add_nic_to_vm(api, vm_id, network_name="rhevm"):
    vm = api.vms.get(id=vm_id)
    nic_params = params.NIC(name='eth0', 
        network=params.Network(name=network_name), 
        interface='virtio')
    return vm.nics.add(nic_params)       

def add_disk_to_vm(api, vm_id, size_gb, storage_domain_name):
    def create_params():
        storage_domain = api.storagedomains.get(storage_domain_name)
        if not storage_domain:
            print "Unable to find storage domain '%s'" % (storage_domain_name)
            return None
        storage_domain_params = params.StorageDomains(storage_domain=[storage_domain])
        disk_params = params.Disk(
            storage_domains=storage_domain_params,
            size=size_gb*GB,
            status=None,
            interface='virtio',
            format='cow',
            sparse=True,
            bootable=False)
        return disk_params

    def issue_add_request(disk_params, attempts=3):
        try:
            vm = api.vms.get(id=vm_id)
            vm.disks.add(disk_params)
        except RequestError, e:
            if "Please try again in a few minutes" in e.detail and attempts > 0:
                print "Waiting to retry adding disk...sleeping 30 seconds"
                time.sleep(30)
                return issue_add_request(disk_params, attempts=attempts-1)
            print e
            return False
        except Exception, e:
            print e
            return False
        return True
    
    disk_params = create_params()
    return issue_add_request(disk_params)


def start_vm(api, vm_id):
    vm = api.vms.get(id=vm_id)
    if vm.status.state != 'up':
        print 'Starting VM'
        for x in range(0,12):
            try:
                vm.start()
                break
            except RequestError, e:
                print e
                print "Will retry"
                time.sleep(10)
                continue

        while api.vms.get(id=vm_id).status.state != 'up':
            print "Waiting for VM to come up"
            time.sleep(5)
    else:
        print 'VM already up'


def get_ip(api, vm_id):
    def __get_ip():
        vm = api.vms.get(id=vm_id)
        info = vm.get_guest_info()
        try:
            return info.get_ips().get_ip()[0].get_address()
        except:
            return None

    # Wait till IP is available
    for x in range(0, 12):
        ip = __get_ip()
        if not ip:
            print "Waiting 10 seconds for IP to become available"
            time.sleep(10)
        else:
            return ip
    return None

def configure_cfme(ipaddr, ssh_username, ssh_password, region, db_password):
    cmd = "appliance_console_cli --region %s --internal --force-key -p %s" % (region, db_password)
    client = SSHClient()
    try:
        client.set_missing_host_key_policy(AutoAddPolicy()) 
        client.connect(ipaddr, username=ssh_username, password=ssh_password, allow_agent=False)
        print "Will run below command on host: %s" % (ipaddr)
        print cmd
        stdin, stdout, stderr = client.exec_command(cmd)
        status = stdout.channel.recv_exit_status()
        out = stdout.readlines()
        err = stderr.readlines()
        return status, out, err
    finally:
        client.close()

if __name__ == "__main__":
    for env_var in [ENV_IP, ENV_USERNAME, ENV_PASSWORD]:
        if env_var not in os.environ:
            print "Please re-run after you have set an environment variable for '%s'" % (env_var)
            sys.exit()
    ip = os.environ[ENV_IP]
    password = os.environ[ENV_PASSWORD]
    username = os.environ[ENV_USERNAME]
    url = "https://%s" % (ip)

    api = API(url=url, username=username, password=password, insecure=True)
    if not api:
        print "Failed to connect to '%s'" % (url)
        sys.exit()

    vm_name = "CloudFormsTest_%s" % time.time()
    vm_template_name = "Imported_CFME_RHEVM_5.3-47"
    storage_domain_name = "VMs"
    cluster_name = "Default"

    template = api.templates.get(vm_template_name)
    if not template:
        print "Couldn't find template with name '%s'" % (vm_template_name)
        sys.exit()

    cluster = api.clusters.get(cluster_name)
    if not cluster:
        print "Couldn't find cluster with name '%s'" % (cluster_name)
        sys.exit()

    vm = create_vm_from_template(api, vm_name=vm_name, cluster=cluster, template=template)
    if not vm:
        print "Unable to create VM from template '%s'" % (vm_template_name)
        sys.exit()

    vm_id = vm.id
    print "VM '%s' with ID: '%s' has been created." % (vm.name, vm.id)

    # Not needed for CFME appliance 5.3
    #add_nic_to_vm(api, vm_id)
    #print "NIC has been added"

    add_disk_to_vm(api, vm_id=vm_id, size_gb=20, storage_domain_name=storage_domain_name)
    print "Disk has been added"

    start_vm(api, vm_id)
    print "VM has been started"

    ip = get_ip(api, vm_id)
    print "VM '%s' has IP Address of '%s'" % (vm_id, ip)

    ssh_username = "root"
    ssh_password = "smartvm"
    region = 1
    db_password = "changeme"

    status, stdout, stderr = configure_cfme(ip, ssh_username, ssh_password, region, db_password)
    if status == 0:
        print "Success configuring the CloudForms Appliance at https://%s" % (ip)
        print "Output from configuring:"
        print stdout
    else:
        print "Unable to configure CloudForms Appliance at '%s'" % (ip)
        print stderr