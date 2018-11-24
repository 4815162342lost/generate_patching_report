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
from create_excel_template import *
from main import *


settings=get_settings()
today = datetime.datetime.now()
args=parcer()

need_patching = not_need_patching = 0
servers_for_patching = []
servers_with_error = []
idx_glob=0

def write_to_file(sheet, idx_glob, contenr, need_reboot):
    global need_patching
    global not_need_patching
    kernel_update = "no"
    csv_writer = return_csv_file_for_single_host(sheet.get_name().lower(), today.strftime("%b_%Y"))
    format_kernel = format['format_green']
    if need_reboot:
        reboot_require = "yes"
        format_reboot = format['format_red']
    else:
        reboot_require="no"
        format_reboot=format['format_green']
    column_width=[]
    try:
        column_width.append(max(len(current_patch) for current_patch in contenr))
    except ValueError:
        column_width.append(20)
    for i in range(1,3):
        column_width.append(10)
    col=0
    for current_patch in contenr:
        if current_patch == 'Summary':
            continue
        if re.search('.*Linux Kernel', current_patch) != -1:
            kernel_update = 'yes'
            format_kernel = format['format_red']
        sheet.write(col + 2, 0, current_patch)
        csv_writer.writerow((current_patch, "none", "none"))
        col+=1
    total_sheet.write(idx_glob + 2, 3, kernel_update, format_kernel)
    total_sheet.write(idx_glob + 2, 4, reboot_require, format_reboot)
    sheet.set_column(0, 0, width=column_width[0])
    if col>0:
        need_patching+=1; servers_for_patching.append(sheet.get_name())
    else:
        not_need_patching+=1
    write_to_total_sheet(col, "security ", sheet, total_sheet, format, idx_glob, 'open_suse')
    write_csv_total(csv_total, sheet.get_name().lower(), kernel_update, reboot_require, col, column_width)

def main_function():
    error_count=0
    servers_list=open('./server_list.txt')
    ssh_con=paramiko.SSHClient()
    ssh_con.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    private_ssh_key = settings['ssh_key']
    ssh_private_key_type = settings['key_type']
    if ssh_private_key_type == "RSA":
        ssh_key = paramiko.RSAKey.from_private_key_file(filename=private_ssh_key)
    elif ssh_private_key_type == "DSA":
        ssh_key = paramiko.DSSKey.from_private_key_file(filename=private_ssh_key)
    for idx_glob, current_server in enumerate(servers_list.readlines()):
        current_server=current_server.rstrip()
        sheet = xls_file.add_worksheet(current_server)
        print('Working with {server} server...'.format(server=current_server))
        try:
            ssh_con.connect(hostname=current_server, username='root', pkey=ssh_key, timeout=30, port=22)
            stdin_check, stdout_check, stderr_check = ssh_con.exec_command(command="zypper list-patches --category security 2>/dev/null | grep '|'", timeout=600)
            stdout_check_1=stdout_check.read().decode().rstrip('\n').split('\n')
            ssh_con.close()
        except (socket.error, paramiko.SSHException):
            print("Connection troubles with server " + termcolor.colored(current_server, "red") + '.')
            write_to_total_sheet("Connection error", "error", sheet, total_sheet, format, idx_glob, 'open_suse')
            error_count+=1
            continue
        except (paramiko.ssh_exception.AuthenticationException, paramiko.BadHostKeyException):
            print("Troubles with authorization on the server  " + termcolor.colored(current_server, "red") + ".")
            write_to_total_sheet("Authorization error", "error", sheet, total_sheet, format, idx_glob, 'open_suse')
            error_count += 1
            continue
        security_patches_list=[]
        need_reboot=False
        for line in stdout_check_1:
            splitted_line=line.split(' | ')
            if len(splitted_line)!=7:
                continue
            if not need_reboot and splitted_line[4].startswith("reboot"):
                need_reboot=True
            security_patches_list.append(splitted_line[6].rstrip())
        write_to_file(sheet, idx_glob, security_patches_list, need_reboot)
        security_patches_list.clear()
    add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format)
    xls_file.close()
    perform_additional_actions(args, today, 'open_suse', xlsx_name, settings, servers_for_patching)


termcolor.cprint("                                                   ' \/ '\n   _  _                        &lt;|\n    \/              __'__     __'__      __'__\n                   /    /    /    /     /    / \n                  /\____\    \____\     \____\               _  _\n                 / ___!___   ___!___    ___!___               \/ \n               // (      (  (      (   (      (\n             / /   \______\  \______\   \______\ \n           /  /   ____!_____ ___!______ ____!_____\n         /   /   /         //         //         / \n      /    /   |         ||         ||         |\n     /_____/     \         \\         \\         \ \n           \      \_________\\_________\\_________\ \n            \         |          |         |\n             \________!__________!_________!________/\n              \|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_|_/|\n               \    _______________                / \n^^^%%%^%^^^%^%%^\_\"/_)/_)_/_)__)/_)/)/)_)_\"_'_\"_//)/)/)/)%%%^^^%^^%%%%^\n^!!^^\"!%%!^^^!^^^!!^^^%%%%%!!!!^^^%%^^^!!%%%%^^^!!!!!!%%%^^^^%^^%%%^^^!", color='red', on_color='on_white')
xlsx_name = 'Linux_list_of_updates_' + str(today.strftime("%B %Y")) + "_Open_Suse.xlsx"
xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)
csv_total=return_csv_for_total(today.strftime("%b_%Y"))
main_function()
