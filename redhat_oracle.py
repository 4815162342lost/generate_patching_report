#!/usr/bin/python3
import os
import re
import socket
import sqlite3
import sys
from distutils.sysconfig import get_python_lib
import paramiko
import termcolor
import xlsxwriter

sys.path.append(get_python_lib())
os.chdir(os.path.dirname(os.path.realpath(__file__)))

#append path to custom modules and import them
sys.path.append('./modules/')
from auto_mm import *
from create_excel_template import *
from send_email import *
from main import *


#create empty lists
servers_for_patching = []
servers_with_error = []

#get arguments from command line (--csv --email)
args=parcer()


# get_file_name
today = datetime.datetime.now()
xlsx_name = 'Linix_List_of_updates_' + str(today.strftime("%B_%Y")) + "_Red_Hat_and_Oracle.xlsx"

#get settings (smtp-server, e-mails, bad-packages) from settings.txt file
settings=get_settings()

error_list = {'yum: not found': "It is Debian or different great distr without yum!",
              'command not found': "It is Debian or different great distr without yum!",
              'RHN support will be disabled': "This system is not registered with RHN",
              'usage: yum [options] COMMAND': "Updateinfo does not compatible with current yum version",
              'No such command: updateinfo': "Updateinfo does not compatible with current yum version",
              'Cannot retrieve repository metadata': 'Incorrect repo, please, fix it',
              'Trying other mirror': 'Please, fix the proxy in /etc/yum.conf',
              'Could not retrieve mirrorlis': 'Please, fix the proxy in /etc/yum.conf'}

# counter for chart
need_patching = not_need_patching = error_count = 0


def write_to_file(contenr, type, sheet, idx_glob, counter):
    '''function for write all dinamyc content to xlsx-file, contenr -- list with patches, type -- patches or error,
    sheet -- xlsx-sheet for write content, idx_glob -- serial number of current server, counter -- number of patches '''
    global need_patching
    global not_need_patching
    sheet.write(0, 1, 'type')
    sheet.write(0, 2, 'available version')
    sheet.write(0, 3, 'current version')
    kernel_update = "no"
    format_kernel = format['format_green']
    reboot_require = "no"
    format_reboot = format['format_green']
    no_potential_risky_packages = "yes"
    format_potential_risky_packages = format['format_green']
    if type == 'patch':
        column0_width = column1_width = column2_width = column3_width = 10
        for row, curren_patch in enumerate(contenr):
            for col, current_content in enumerate(curren_patch[0][0:]):
                sheet.write(row + 1, col, current_content)
                if col == 0 and len(current_content) > column0_width:
                    column0_width = len(current_content)
                elif col == 1 and len(current_content) > column1_width:
                    column1_width = len(current_content)
                elif col == 2:
                    if len(current_content) > column2_width:
                        column2_width = len(current_content)
                    if no_potential_risky_packages == "yes":
                        for current_bad in settings['bad_packages']:
                            if str(current_content).startswith(current_bad):
                                if str(current_content).startswith("mysql-libs") or str(current_content).startswith(
                                        "mariadb-libs"):
                                    continue
                                no_potential_risky_packages = "no"
                                format_potential_risky_packages = format['format_red']
                                break
                    if kernel_update == "no":
                        if current_content.startswith("kernel") or current_content.startswith("linux-image"):
                            kernel_update = 'yes'
                            reboot_require = 'yes'
                            format_kernel = format['format_red']
                            format_reboot = format['format_red']
                    if reboot_require == "no":
                        for current_package in packages_which_require_reboot:
                            if str(current_content).startswith(current_package) or current_content.find(
                                    '-firmware-') != -1:
                                reboot_require = 'yes'
                                format_reboot = format['format_red']
                                break
            sheet.write(row + 1, 3, curren_patch[1])
            if len(curren_patch[1]) > column3_width:
                column3_width = len(curren_patch[1])
        total_sheet.write(idx_glob + 2, 3, kernel_update, format_kernel)
        total_sheet.write(idx_glob + 2, 4, reboot_require, format_reboot)
        total_sheet.write(idx_glob + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
        sheet.set_column(0, 0, width=column0_width)
        sheet.set_column(1, 1, width=column1_width)
        sheet.set_column(2, 2, width=column2_width)
        sheet.set_column(3, 3, width=column3_width)

        if counter == 0:
            not_need_patching += 1
            sheet.set_tab_color("#79eca3")
            sheet.write(0, 0, "security patches are not required")
            total_sheet.write(idx_glob + 2, 1, "All security packages are up to date", format['format_green'])
            total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_green'])
        elif counter == 1:
            servers_for_patching.append(sheet.get_name())
            need_patching += 1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(contenr) + " security patch is available")
            total_sheet.write(idx_glob + 2, 1, "Only 1 security patch is available", format['format_red'])
            total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_red'])
        elif counter > 1:
            servers_for_patching.append(sheet.get_name())
            need_patching += 1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(contenr) + " security patches are available")
            total_sheet.write(idx_glob + 2, 1, str(counter) + " security pathes are available", format['format_red'])
            total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_red'])
    elif type == 'error':
        servers_with_error.append(sheet.get_name())
        total_sheet.write(idx_glob + 2, 1, "error: " + str(contenr), format['format_purple'])
        total_sheet.write(idx_glob + 2, 0, sheet.get_name(), format['format_purple'])
        total_sheet.write(idx_glob + 2, 3, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 4, "unknown", format['format_purple'])
        total_sheet.write(idx_glob + 2, 5, "unknown", format['format_purple'])


def find_error(ssh_connection, std_error, std_stdout, sheet, idx_glob):
    global error_count
    std_error_1 = std_error.read().decode()
    #    std_stdout_1= std_stdout.read().decode()
    for error in error_list.keys():
        if std_error_1.find(error) != -1 or std_stdout.find(error) != -1:
            print("Critical error with server", termcolor.colored(sheet.get_name() + '.', color='red'),
                  error_list[error])
            error_count += 1
            sheet.write(0, 0, error_list[error])
            sheet.set_tab_color("purple")
            write_to_file(error_list[error], "error", sheet, idx_glob, 0)
            ssh_connection.close()
            return True
    return False



def main():
    server_list_file = open('server_list.txt', 'r')
    server_list = server_list_file.read().rstrip().split('\n')
    server_list_file.close()
    private_ssh_key = settings['ssh_key']
    ssh_private_key_type = settings['key_type']
    if ssh_private_key_type == "RSA":
        private_key = paramiko.RSAKey.from_private_key_file(filename=private_ssh_key)
    elif ssh_private_key_type == "DSA":
        private_key = paramiko.DSSKey.from_private_key_file(filename=private_ssh_key)
    ssh_connection = paramiko.SSHClient()
    ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    global error_count
    servers_count = len(server_list)
    for idx_glob, server in enumerate(server_list):
        print(termcolor.colored(
            server + "({idx_glob}/{servers_count})".format(idx_glob=idx_glob + 1, servers_count=servers_count),
            color='grey', on_color='on_green'))
        patches = []
        sheet = xls_file.add_worksheet(str(server))
        try:
            ssh_connection.connect(hostname=server, username='root', port=22, pkey=private_key, timeout=60)
            print("Trying to clean yum cache...")
            ssh_stdin, ssh_stdout_clean_repo, ssh_stderr = ssh_connection.exec_command(
                'ls /var/run/yum.pid >/dev/null 2>&1 || yum clean all')
            if find_error(ssh_connection, ssh_stderr, ssh_stdout_clean_repo.read().decode(), sheet, idx_glob):
                continue
            print("geting security patches list...")
            ssh_stdin, proc, ssh_stderr = ssh_connection.exec_command(
                'ls /var/run/yum.pid >/dev/null 2>&1 || yum -q updateinfo list security updates')
            proc_tmp = proc.read().decode()
            if find_error(ssh_connection, ssh_stderr, proc_tmp, sheet, idx_glob):
                continue
            ssh_stdin, proc_all_installed_packages, ssh_stderr = ssh_connection.exec_command('rpm -qa')
        except (socket.error, paramiko.SSHException):
            print("Connection troubles with server " + termcolor.colored(server,
                                                                         "red") + ". Can not clear the yum cache.")
            sheet.write(0, 0, "Connection troubles")
            sheet.set_tab_color("purple")
            write_to_file('connection troubles', "error", sheet, idx_glob, 0)
            error_count += 1
            continue
        except (paramiko.ssh_exception.AuthenticationException, paramiko.BadHostKeyException):
            print("Troubles with aouthorization on the server  " + termcolor.colored(server, "red") + ".")
            sheet.write(0, 0, "Troubles with authorization")
            sheet.set_tab_color("purple")
            write_to_file('Troubles with authorization', "error", sheet, idx_glob, 0)
            error_count += 1
            continue
        patches_list = proc_tmp.rstrip("\n").split("\n")
        all_rpm_list = proc_all_installed_packages.read().decode().rstrip("\n").split("\n")
        ssh_connection.close()
        previous_patch = "";
        previous_patch_for_write = ["", "", "", ""]
        counter = 0;
        counter_2 = 0
        previous_number_position = None
        for idx, current_patch in enumerate(patches_list):
            if not current_patch:
                break
            current_patch_split = re.split(" +", current_patch)
            if len(current_patch_split) != 3:
                print(termcolor.colored("Warning: ", color="yellow",
                                        on_color="on_grey") + "There are error with patch: " + str(current_patch))
                continue
            try:
                number_position = re.search("-\d", current_patch_split[2])
                # id first correct element!=idx
                counter_2 += 1
                if not number_position:
                    print(termcolor.colored("Warning: ", color="yellow",
                                            on_color="on_grey") + "There are error with patch: " + str(current_patch))
                    counter_2 -= 1
                    continue
            # if patch does not exists (current_patch_split[2])
            except IndexError:
                print(termcolor.colored("Warning: ", color="yellow",
                                        on_color="on_grey") + "There are error with patch: " + str(current_patch))
                continue
            # if first element and patches counter >1
            if idx == 0 and len(patches_list) > 1 or counter_2 == 1 and len(patches_list) > 1:
                previous_patch_for_write = current_patch_split
                previous_patch = current_patch_split[2][:number_position.start()]
                previous_number_position = number_position
            # if not first element or patches count=1
            else:
                # if not only one patch
                if len(patches_list) > 1:
                    # if current patch is previuos patch
                    if current_patch_split[2][:number_position.start()] == previous_patch:
                        previous_patch_for_write = current_patch_split
                    else:
                        # search curent version of package
                        for current_rpm in all_rpm_list:
                            try:
                                if current_rpm[:previous_number_position.start()] == previous_patch and \
                                        current_rpm[previous_number_position.start() + 1:][0].isdigit():
                                    patches.append((previous_patch_for_write, current_rpm))
                                    previous_patch_for_write = current_patch_split
                                    previous_patch = current_patch_split[2][:number_position.start()]
                                    previous_number_position = number_position
                                    counter += 1
                                    break
                            except IndexError:
                                pass
                        else:
                            counter_2 -= 1
                            print(termcolor.colored("Warning: ", color="yellow",
                                                    on_color="on_grey") + "There are error with patch: " + str(
                                current_patch))
                # if last element
                if idx == len(patches_list) - 1:
                    for current_rpm in all_rpm_list:
                        try:
                            if current_rpm[:number_position.start()] == current_patch_split[2][
                                                                        :number_position.start()] and \
                                    current_rpm[number_position.start() + 1:][0].isdigit():
                                patches.append((current_patch_split, current_rpm))
                                counter += 1
                                break
                        except IndexError:
                            pass
        write_to_file(patches, "patch", sheet, idx_glob, counter)

    if args.csv == 'yes' and servers_for_patching:
        db_con = sqlite3.connect('./patching.db')
        db_cur = db_con.cursor()
        error_list_from_csv = working_with_csv(servers_for_patching, db_cur, today, 'redhat_oracle')
        if error_list_from_csv:
            termcolor.cprint("Maintenance mode will be incorrect:\n" + ',\n'.join(error_list_from_csv), color='magenta',
                             on_color='on_white')
        db_cur.close()
    add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format)
    xls_file.close()
    if args.email != None:
        if send_mail(args.email, settings['email_from'], settings['smtp_server'],  xlsx_name, today, 'Patching list for RedHat\Oracle '):
            print("All done, the file \"{file_name}\" has been sent to e-mail {mail_address}".format(file_name=xlsx_name,
                                                                                                 mail_address=args.email))
    else:
        print("All done. Please, see the file \"" + xlsx_name + "\". Have a nice day!")


termcolor.cprint(
    "              .-. \n        .-'``(|||) \n     ,`\ \    `-`.               88                         88 \n    /   \ '``-.   `              88                         88 \n  .-.  ,       `___:    88   88  88,888,  88   88  ,88888, 88888  88   88 \n (:::) :        ___     88   88  88   88  88   88  88   88  88    88   88 \n  `-`  `       ,   :    88   88  88   88  88   88  88   88  88    88   88 \n    \   / ,..-`   ,     88   88  88   88  88   88  88   88  88    88   88 \n     `./ /    .-.`      '88888'  '88888'  '88888'  88   88  '8888 '88888' \n       `-..-(   ) \n              `-` ",
    "yellow", "on_grey")
# .*-firmware-*
packages_which_require_reboot = ("glibc", "hal", "systemd", "udev")


xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)
db_cur=sqlite(args.csv)
main()
