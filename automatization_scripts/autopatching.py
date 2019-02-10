#!/usr/bin/python3
import paramiko
import sqlite3
import datetime
import argparse
import configparser
import re
import time

def patching_rhel_based(server_name, ssh_connection, db_con, os_type):
    """Function for patch Centos"""
    stdin, stdout, stderr = ssh_connection.exec_command("cat /etc/system-release | grep -o  '[0-9]' | head -n 1")
    centos_version=stdout.read().decode().rstrip()
    stdin, stdout, stderr = ssh_connection.exec_command('ls /var/run/yum.pid >/dev/null 2>&1')
    #yum.pid does not exist, need perform patching
    if stdout.channel.recv_exit_status() == 1 or stdout.channel.recv_exit_status() == 2:
        if os_type == 'centos':
            stdin, stdout, stderr = ssh_connection.exec_command('yes | yum update -q  --nogpgcheck')
        elif os_type == 'redhat':
            stdin, stdout, stderr = ssh_connection.exec_command('yes | yum update --security -q  --nogpgcheck')
        if stdout.channel.recv_exit_status() == 1:
            print('Patching failed!')
            #print(stderr.read().decode().replace("\n\n", '\n'))
        elif stdout.channel.recv_exit_status() == 0:
            print('patching completed!')
            #print(stdout.read().decode().replace("\n\n", '\n'))
            #print(stderr.read().decode().replace("\n\n", "\n"))
            #check need to reboot or not and reboot
            if centos_version == '7':
                stdin, stdout, stderr = ssh_connection.exec_command('needs-restarting -r')
                if stdout.channel.recv_exit_status() == 1:
                    print('reboot is required. Rebooting in one minute')
                    ssh_connection.exec_command('shutdown -r 1')
                    return 1
                else:
                    print('reboot is not needed after patching')
                    return 0
    else:
        print('yum alreasy running, exiting...')

def parse_args():
    """Parse arguments"""
    args=argparse.ArgumentParser()
    args.add_argument("-s", "--servers", type=str, required=True, help="Servers for autopatching divided by comma")
    return args.parse_args()

def config_parser():
    """Function for configuration parser"""
    conf_parser=configparser.ConfigParser()
    conf_parser.read('./settings.cfg')
    return conf_parser['auto_patching']


def get_listened_ports(ssh_connection):
    """Function for get listened ports"""
    stdin, stdout, stderr = ssh_connection.exec_command('netstat -lntup | tail -n +3')
    listened_ports={}
    for line in stdout.read().decode().rstrip().split('\n'):
        splitted_lines=re.split(" +", line.rstrip())
        port_number=splitted_lines[3].split(':')[-1]
        application=splitted_lines[-1].split('/')[-1]
        listened_ports[port_number] = application
    return listened_ports

def main():
    settings=config_parser()
    servers_for_patching=parse_args().servers.split(',')
    sqlite_db=sqlite3.connect("./patching_dev.db")
    db_cur=sqlite_db.cursor()
    if settings['key_type'] == 'RSA':
        ssh_private_key = paramiko.RSAKey.from_private_key_file(filename=settings['ssh_key'])
    elif settings['key_type'] == 'DSA':
        ssh_private_key = paramiko.DSSKey.from_private_key_file(filename=settings['ssh_key'])
    ssh_connection=paramiko.SSHClient()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    for current_server in servers_for_patching:
        os_type, autopatching=db_cur.execute("SELECT OS, AUTOMATIC_PATCHING FROM SERVERS WHERE SERVER_NAME=:server_name COLLATE NOCASE", {'server_name' : current_server}).fetchone()
        if not autopatching:
            continue
        try:
            ssh_connection.connect(hostname=current_server.rstrip(), pkey=ssh_private_key, username='root', port=22)
            listening_ports_before_patching=get_listened_ports(ssh_connection)
            if os_type == 'centos' or os_type == 'redhat':
                need_reboot=patching_rhel_based(current_server, ssh_connection, db_cur, os_type)
                #1 if ned reboot
                if need_reboot:
                    ssh_connection.exec_command('shutdown -r 1')
                    ssh_connection.close()
                    time.sleep(120)
                    try:
                        ssh_connection.connect(hostname=current_server.rstrip(), pkey=ssh_private_key, username='root',port=22)
                    except:
                        print('Can not connect to server after reboot!!!')
                    listening_ports_after_patching=get_listened_ports(ssh_connection)
                    diff_in_ports_before_and_after_patching=set(listening_ports_before_patching) - set(listening_ports_after_patching)
                    if diff_in_ports_before_and_after_patching:
                        print("Perhaps following applications did not start after reboot:")
                        for current_port in diff_in_ports_before_and_after_patching:
                            print('aplication: {app}, port: {port}'.format(app=listening_ports_before_patching[current_port], port=current_port))
            ssh_connection.close()
        except 0:
            print("Error during ssh-connection")
main()
