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
from auto_mm import *
from create_excel_template import *
from send_email import *
from main import *
from auto_snapshots import *


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
    format_kernel = format['format_green']
    if need_reboot:
        reboot_require = "yes"
        format_reboot = format['format_red']
    else:
        reboot_require="no"
        format_reboot=format['format_green']
    no_potential_risky_packages = "yes"
    format_potential_risky_packages = format['format_green']
    column0_width = 10
    col=0
    for current_patch in contenr:
        if current_patch == 'Summary':
            continue
        if len(current_patch)>column0_width:
            column0_width=len(current_patch)
        if no_potential_risky_packages=='yes':
            for current_bad in settings['bad_packages']:
                if current_patch.find(current_bad)!=-1:
                    no_potential_risky_packages='no'
                    format_potential_risky_packages=format['format_red']
                    break
        if re.search('.*Linux Kernel', current_patch) != -1:
            kernel_update = 'yes'
            format_kernel = format['format_red']
        sheet.write(col + 2, 0, current_patch)
        col+=1
    total_sheet.write(idx_glob + 2, 3, kernel_update, format_kernel)
    total_sheet.write(idx_glob + 2, 4, reboot_require, format_reboot)
    total_sheet.write(idx_glob + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
    sheet.set_column(0, 0, width=column0_width)
    if col>0:
        need_patching+=1; servers_for_patching.append(sheet.get_name())
    else:
        not_need_patching+=1
    write_to_total_sheet(col, "security ", sheet, total_sheet, format, idx_glob, 'open_suse')

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
    if args.csv == 'yes' and servers_for_patching:
        error_list_from_csv = working_with_csv(servers_for_patching, db_cur, today, 'open_suse')
        if error_list_from_csv:
            termcolor.cprint("Maintenance mode will be incorrect:\n" + ',\n'.join(error_list_from_csv), color='magenta',
                              on_color='on_white')
    if args.snap=='yes' and servers_for_patching:
        servers_whcih_require_snap_without_additional_activities=snap_determine_needed_servers(db_cur, servers_for_patching)
        snap_create_csv_file(db_cur, servers_whcih_require_snap_without_additional_activities, "auto-snapshots_open_suse_{month}.csv".format(month=today.strftime("%B")), today)
    if args.csv == 'yes' or args.snap=='yes':
        db_cur.close()
    add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format)
    xls_file.close()
    if args.email != None:
        send_mail(args.email, settings['email_from'], settings['smtp_server'],  xlsx_name, today, 'Patching list for Open_Suse ')
        print("All done, the file \"{file_name}\" has been sent to e-mail {mail_address}".format(file_name=xlsx_name,
                                                                                                 mail_address=args.email))
    else:
        print("All done. Please, see the file \"" + xlsx_name + "\". Have a nice day!")


termcolor.cprint("____________________________________________________________________\n                                                 _,-\"-._        tbk\n                 <_     _>\n     _____----\"----________________________________`---'_______\n    /----------------------------------------------------------\ \n   /] [_] #### [___] #### [___]  \/  [___] #### [___] #### [_] [\ \n  /----------------------------11407-----------------------|-|---\ \n  |=          S  B  B                          C  F  F     |_|  =|\n[=|______________________________________________________________|=]\n   )/_-(-o-)=_=(=8=)=_=(-o-)-_ [____] _-(-o-)=_=(=8=)=_=(-o-)-_\(\n====================================================================\nSBB CFF FFS  Ae 6/6  (1952)  Co'Co'  125 km/h  4300 kW", color='red', on_color='on_white')
xlsx_name = 'Liniux_list_of_updates_' + str(today.strftime("%B %Y")) + "_Open_Suse.xlsx"
xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)
db_cur=sqlite(args.csv, args.snap)

main_function()
