#! /usr/bin/env python
import os
import sys

try:
    from ovirtsdk.api import API
    from ovirtsdk.xml import params
except:
    print "Please re-run after you have installed 'ovirt-engine-sdk-python'"
    print "Example: easy_install ovirt-engine-sdk-python"
    sys.exit()


ENV_IP = "OVIRT_IP"
ENV_USERNAME = "OVIRT_USERNAME"
ENV_PASSWORD = "OVIRT_PASSWORD"


def get_all_vms(api):
    return api.vms.list()

def print_all_vms(api):
    vms = get_all_vms(api)
    for vm in vms:
        print "Name: %s,  IP: %s" % (vm.name, get_guest_ip(vm))

def get_guest_ip(vm):
    info = vm.get_guest_info()
    if info is None:
        return None
    return info.get_ips().get_ip()[0].get_address()

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

    print_all_vms(api)

    vms2 = api.vms.list(query='name=CloudForms_JWM')
    if vms2:
        vm = vms2[0]
        print vm.name
        print get_guest_ip(vm)

