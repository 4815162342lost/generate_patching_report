#!/usr/bin/python3
import paramiko
import termcolor
import xlsxwriter
import os
os.chdir(os.path.dirname(os.path.realpath(__file__)))
import datetime
import re

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
    global need_patching
    global not_need_patching
    if type == 'patch':
        csv_writer = return_csv_file_for_single_host(sheet.get_name().lower(), today.strftime("%b_%Y"))
        kernel_update = reboot_require = "no"
        format_kernel = format_reboot = format['format_green']
        column_width=[]
        if reboot_require=='no' and 'systemd' in contenr.keys():
            reboot_require='yes'
            format_reboot=format['format_red']
        for col, current_patch in enumerate(contenr.keys()):
            if kernel_update == 0 and re.search('linux-image.+', current_patch):
                kernel_update = reboot_require = 'yes'
                format_kernel = format_reboot = format['format_red']
            sheet.write_row(col+2, 0, (current_patch, contenr[current_patch][1], contenr[current_patch][0]), format['format_border'])
            csv_writer.writerow((current_patch, contenr[current_patch][1], contenr[current_patch][0]))
        total_sheet.write(idx_glob + 2, 3, kernel_update, format_kernel)
        total_sheet.write(idx_glob + 2, 4, reboot_require, format_reboot)
        write_to_total_sheet(len(contenr.keys()), 'security', sheet, total_sheet, format, idx_glob, 'debian')
        if len(contenr.keys())>0:
            servers_for_patching.append(sheet.get_name())
            need_patching+=1
            column_width.append(max(len(current_var) for current_var in contenr.keys()))
            column_width.append(max(len(contenr[current_var][1]) for current_var in contenr.keys()))
            column_width.append(max(len(contenr[current_var][0]) for current_var in contenr.keys()))
            for idx, current_column in enumerate(column_width):
                sheet.set_column(idx, idx, width=current_column)
        else:
            not_need_patching+=1
            sheet.set_column(0, 0, width=20)
            for i in range(3):
                column_width.append(0)
        write_csv_total(csv_total, sheet.get_name().lower(), kernel_update, reboot_require, len(contenr.keys()), column_width)
    if type == 'error':
        global error_count
        error_count+=1
        servers_with_error.append(sheet.get_name())
        sheet.write(0,0,"Unknow error", format["format_bold"])
        sheet.set_column(0, 0, width=20)
        sheet.set_tab_color("purple")
        total_sheet.write(idx_glob + 2, 1, "error: " + str(contenr), format['format_purple'])
        total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_purple'])
        total_sheet.write(idx_glob + 2, 3, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 4, "unknown", format['format_purple'])


def main_function():
    global error_count
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
        try:
            sheet = xls_file.add_worksheet(current_server)
            ssh_con.connect(hostname=current_server, username='root', pkey=ssh_key, timeout=30, port=22)
            stdin_check, stdout_check, stderr_check = ssh_con.exec_command(command='apt update',  timeout=1200)
            a=stderr_check.read().decode()
            stdin_check, stdout_check, stderr_check = ssh_con.exec_command(command="unattended-upgrade --dry-run -d 2>/dev/null | grep 'Checking' | awk '{ print $2 }'", timeout=1200)
            print('Trying to perform apt list --upgradable command')
            stdin_all_version, stdout_all_version, stderr_all_version = ssh_con.exec_command(command="apt list --upgradable 2>/dev/null | tail -n +2", timeout=1200)
            stdout_check_1=stdout_check.read().decode().rstrip('\n').split('\n')
            stdout_all_version_1=stdout_all_version.read().decode().rstrip('\n').split('\n')
            ssh_con.close()
            for current_package in stdout_all_version_1:
                current_package_formated = current_package.split(' ')
                if current_package_formated[0][:str(current_package_formated).find('/') - 2] in stdout_check_1:
                    all_packages[current_package_formated[0][:str(current_package_formated).find('/') - 2]] = (
                    current_package_formated[1], current_package_formated[5][:-1])
            write_to_file(all_packages, 'patch', sheet, idx_glob)
            all_packages.clear()
        except:
            write_to_file("Connection issue", "error", sheet, idx_glob)
            print('Critical error, skip this server...')
    add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format)
    xls_file.close()
    perform_additional_actions(args, today, 'debian', xlsx_name, settings, servers_for_patching)


termcolor.cprint("____________________________________________________________________\n                                                 _,-\"-._        tbk\n                 <_     _>\n     _____----\"----________________________________`---'_______\n    /----------------------------------------------------------\ \n   /] [_] #### [___] #### [___]  \/  [___] #### [___] #### [_] [\ \n  /----------------------------11407-----------------------|-|---\ \n  |=          S  B  B                          C  F  F     |_|  =|\n[=|______________________________________________________________|=]\n   )/_-(-o-)=_=(=8=)=_=(-o-)-_ [____] _-(-o-)=_=(=8=)=_=(-o-)-_\(\n====================================================================\nSBB CFF FFS  Ae 6/6  (1952)  Co'Co'  125 km/h  4300 kW", color='red', on_color='on_white')
xlsx_name = 'Linux_list_of_updates_' + str(today.strftime("%B %Y")) + "_Debian.xlsx"
xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)
csv_total=return_csv_for_total(today.strftime("%b_%Y"))
main_function()
