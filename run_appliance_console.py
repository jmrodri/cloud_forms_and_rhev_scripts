#!/usr/bin/env python

import sys

try:
    from paramiko import AutoAddPolicy
    from paramiko.client import SSHClient
except:
    print "Please re-run after you have installed 'paramiko'"
    print "Example: easy_install paramiko"
    sys.exit()


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

    if len(sys.argv) < 2:
        print "Please re-run with an IP address of the CFME VM"
        sys.exit()

    ipaddr = sys.argv[1]
    ssh_username = "root"
    ssh_password = "smartvm"
    region = 1
    db_password = "changeme"

    status, stdout, stderr = configure_cfme(ipaddr, ssh_username, ssh_password, region, db_password)
    print "Exit Status: %s" % (status)
    print "STDOUT"
    print stdout
    print "\n\nSTDERR"
    print stderr