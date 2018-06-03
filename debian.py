#!/usr/bin/python3
import paramiko
import termcolor
import xlsxwriter
import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))
import datetime
import re
import socket

import sys
sys.path.append('./modules/')
os.chdir(os.path.dirname(os.path.realpath(__file__)))
from create_excel_template import *
from main import *

settings=get_settings()
today = datetime.datetime.now()
args=parcer()


need_patching = not_need_patching = error_count = 0
servers_for_patching = []
servers_with_error = []
idx_glob=0

def write_to_file(contenr, type, sheet, idx_glob):
    if type == 'patch':
        kernel_update = "no"
        format_kernel = format['format_green']
        reboot_require = "no"
        format_reboot = format['format_green']
        no_potential_risky_packages = "yes"
        format_potential_risky_packages = format['format_green']
        column0_width = column1_width = column2_width = 10
        if reboot_require=='no' and 'systemd' in contenr.keys():
            reboot_require='yes'
            format_reboot=format['format_red']
        for col, current_patch in enumerate(contenr.keys()):
            if len(current_patch)>column0_width:
                column0_width=len(current_patch)
            if len(contenr[current_patch][0])>column2_width:
                column2_width=len(contenr[current_patch][0])
            if len(contenr[current_patch][1])>column1_width:
                column1_width=len(contenr[current_patch][1])
            if no_potential_risky_packages=='yes':
                for current_bad in settings['bad_packages']:
                    if current_patch.startswith(current_bad):
                        no_potential_risky_packages='no'
                        format_potential_risky_packages=format['format_red']
                        break
            if re.search('linux-image.+', current_patch):
                kernel_update = reboot_require = 'yes'
                format_kernel = format_reboot = format['format_red']
            sheet.write(col + 2, 0, current_patch)
            sheet.write(col + 2, 1, contenr[current_patch][1])
            sheet.write(col + 2, 2, contenr[current_patch][0])
        total_sheet.write(idx_glob + 2, 3, kernel_update, format_kernel)
        total_sheet.write(idx_glob + 2, 4, reboot_require, format_reboot)
        total_sheet.write(idx_glob + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
        sheet.set_column(0, 0, width=column0_width)
        sheet.set_column(1, 1, width=column1_width)
        sheet.set_column(2, 2, width=column2_width)
        write_to_total_sheet(len(contenr.keys()), 'security', sheet, total_sheet)
    if type == 'error':
        global error_count
        error_count+=1
        servers_with_error.append(sheet.get_name())
        total_sheet.write(idx_glob + 2, 1, "error: " + str(contenr), format['format_purple'])
        total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_purple'])
        total_sheet.write(idx_glob + 2, 3, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 4, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 5, "unknown", format['format_purple'])


def main_function():
    servers_list=open('./server_list.txt')
    ssh_con=paramiko.SSHClient()
    ssh_con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    private_ssh_key = settings['ssh_key']
    ssh_private_key_type = settings['key_type']
    if ssh_private_key_type == "RSA":
        ssh_key = paramiko.RSAKey.from_private_key_file(filename=private_ssh_key)
    elif ssh_private_key_type == "DSA":
        ssh_key = paramiko.DSSKey.from_private_key_file(filename=private_ssh_key)
    all_packages={}
    for idx_glob, current_server in enumerate(servers_list.readlines()):
        current_server=current_server.rstrip()
        print('Working with {server} server...'.format(server=current_server))
        ssh_con.connect(hostname=current_server, username='root', pkey=ssh_key, timeout=30, port=22)
        stdin_check, stdout_check, stderr_check = ssh_con.exec_command(command='apt update',  timeout=600)
        a=stderr_check.read().decode()
        stdin_check, stdout_check, stderr_check = ssh_con.exec_command(command="unattended-upgrade --dry-run -d 2>/dev/null | grep 'Checking' | awk '{ print $2 }'", timeout=600)
        print('Trying to perform apt list --upgradable command')
        stdin_all_version, stdout_all_version, stderr_all_version = ssh_con.exec_command(command="apt list --upgradable 2>/dev/null | tail -n +2", timeout=600)
        stdout_check_1=stdout_check.read().decode().rstrip('\n').split('\n')
        stdout_all_version_1=stdout_all_version.read().decode().rstrip('\n').split('\n')
        ssh_con.close()
        sheet = xls_file.add_worksheet(current_server)
        for current_package in stdout_all_version_1:
            current_package_formated = current_package.split(' ')
            if current_package_formated[0][:str(current_package_formated).find('/') - 2] in stdout_check_1:
                all_packages[current_package_formated[0][:str(current_package_formated).find('/') - 2]] = (
                current_package_formated[1], current_package_formated[5][:-1])
        write_to_file(all_packages, 'patch', sheet, idx_glob)
        all_packages.clear()
    xls_file.close()
    perform_additional_actions(args, today, 'debian', xlsx_name, settings, servers_for_patching)


termcolor.cprint("____________________________________________________________________\n                                                 _,-\"-._        tbk\n                 <_     _>\n     _____----\"----________________________________`---'_______\n    /----------------------------------------------------------\ \n   /] [_] #### [___] #### [___]  \/  [___] #### [___] #### [_] [\ \n  /----------------------------11407-----------------------|-|---\ \n  |=          S  B  B                          C  F  F     |_|  =|\n[=|______________________________________________________________|=]\n   )/_-(-o-)=_=(=8=)=_=(-o-)-_ [____] _-(-o-)=_=(=8=)=_=(-o-)-_\(\n====================================================================\nSBB CFF FFS  Ae 6/6  (1952)  Co'Co'  125 km/h  4300 kW", color='red', on_color='on_white')
xlsx_name = 'Linux_list_of_updates_' + str(today.strftime("%B %Y")) + "_Debian.xlsx"
xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)

main_function()
