#! /usr/bin/env python

import os
import subprocess
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


ENV_IP = "OVIRT_IP"
ENV_USERNAME = "OVIRT_USERNAME"
ENV_PASSWORD = "OVIRT_PASSWORD"


def run_command(cmd):
    print "Running: %s" % (cmd)
    handle = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out_msg, err_msg = handle.communicate(None)
    return handle.returncode, out_msg, err_msg

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

    cfme_image_file = "./cfme-rhevm-5.3-47.x86_64.rhevm.ova"
    imported_template_name = "zeus_cfme-rhevm-5.3-47_%s" % (time.time())
    export_domain_name = "export"
    storage_domain_name = "VMs"
    cluster_name = "Default"
    data_center_name = "Default"

    if not os.path.exists(cfme_image_file):
        print "Unable to find '%s'" % (cfme_image_file)
        sys.exit()

    # Verify Export domain exists
    data_center = api.datacenters.get(data_center_name)
    export_domain = data_center.storagedomains.get(export_domain_name)
    if not export_domain:
        print "Unable to find export domain '%s'" % (export_domain_name)
        sys.exit()
    if export_domain.status.state != "active":
        print "Export domain '%s' is in unexpected state '%s'" % (export_domain_name, export_domain.state)
        sys.exit()

    print "Verified export domain exists: '%s' on '%s'" % (export_domain_name, ip)
    ###
    # We will scp file to ovirt engine, then ssh and execute engine-image-uploaded local to the ovirt engine node
    # Alternative is we run 'rhevm-image-uploaded' from the Satellite node.
    #  We need to install 'rhevm-image-uploader' RPM
    #  use "-r" of 'rhevm-image-uploader' to specify remote ovirt engine node address
    ###

    # Commenting out for now since it's taking ~15 mins to complete the scp testing over VPN
    # scp file to engine node root home directory
    #cmd = "scp -o \'StrictHostKeyChecking no\' '%s' root@%s:~/" % (cfme_image_file, ip)
    #status, out, err = run_command(cmd)
    #if status:
    #    print "Error running: %s" % (cmd)
    #    print err
    #    sys.exit()

    # ssh to engine node and upload the image in the home directory
    # engine-image-uploader -N cfme-rhevm-5.3-47 -e export -v -m upload ./cfme-rhevm-5.3-47.x86_64.rhevm.ova
    engine_image_upload_cmd = "engine-image-uploader -u %s -p \'%s\' -N %s -e %s -m upload ~/%s" % (username, password, imported_template_name, export_domain_name, cfme_image_file)
    cmd = "ssh root@%s -o \'StrictHostKeyChecking no\' -C '%s'" % (ip, engine_image_upload_cmd)
    status, out, err = run_command(cmd)
    if status:
        print "Error running:  %s" % (cmd)
        print err
        sys.exit()

    print "Uploaded '%s' as '%s' to export domain '%s' on '%s'" % (cfme_image_file, imported_template_name, export_domain_name, ip)
    print out

    # Import appliance as a VM template
    data_center = api.datacenters.get(data_center_name)
    export_domain = api.storagedomains.get(export_domain_name)
    storage_domain = api.storagedomains.get(storage_domain_name)
    cluster = api.clusters.get(name=cluster_name)

    import_template_params = params.Action(storage_domain=storage_domain, 
        cluster=cluster)

    export_domain.templates.get(imported_template_name).import_template(import_template_params)
    print 'Template was imported successfully'
    print 'Waiting for Template to reach "ok" status'
    while api.templates.get(imported_template_name).status.state != 'ok':
        time.sleep(1)
