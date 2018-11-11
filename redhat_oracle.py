#!/usr/bin/python3
import os
import re
import socket
import sys
from distutils.sysconfig import get_python_lib
import paramiko
import termcolor
import xlsxwriter
import datetime
import logging
import csv

sys.path.append(get_python_lib())
os.chdir(os.path.dirname(os.path.realpath(__file__)))

logging.basicConfig(filename="./redhat_patching_log.txt", filemode='a', level=logging.INFO, format="%(asctime)s %(message)s" ,datefmt="%d/%m/%Y %H:%M:%S")
logging.info("Starting the script")

#append path to custom modules and import them
sys.path.append('./modules/')
from create_excel_template import *
from main import *

#create empty lists for servers which will be patched
servers_for_patching = []

#get arguments from command line (--csv --email)
args=parcer()

# set xlsx-file name
today = datetime.datetime.now()
xlsx_name = 'Linix_list_of_updates_' + str(today.strftime("%B_%Y")) + "_Red_Hat_and_Oracle.xlsx"

#get settings (smtp-server, e-mails, bad packages and etc.) from settings.txt file
settings=get_settings()

#set error list
error_list = {'yum: not found': "It is Debian or different great distr without yum!",
              'command not found': "It is Debian or different great distr without yum!",
              'RHN support will be disabled': "This system is not registered with RHN",
              'usage: yum [options] COMMAND': "Updateinfo does not compatible with current yum version",
              'No such command: updateinfo': "Updateinfo does not compatible with current yum version",
              'Cannot retrieve repository metadata': 'Incorrect repo, please, fix it',
              'Could not retrieve mirrorlis': 'Please, fix the proxy in /etc/yum.conf'}

# counter for chart (add_chart function)
need_patching = not_need_patching = error_count = 0


def write_to_file(contenr, sheet, idx_glob, counter):
    '''function for write all dynamic content to xlsx-file, contenr -- list with patches (see below),
    sheet -- xlsx-sheet for write content, idx_glob -- serial number of current server, counter -- number of patches'''
    #example of the contenr value: ['NetworkManager', '1:1.8.0-9.el7.x86_64', '1.4.0-20.el7_3.x86_64']
    global need_patching
    global not_need_patching
    global servers_for_patching
    kernel_update = reboot_require = "no"
    format_kernel = format_reboot = format['format_green']
    csv_file_for_server=open('./rhel_based/' + sheet.get_name().lower(), 'w')
    csv_writer=csv.writer(csv_file_for_server, delimiter=';')
    csv_writer.writerow(("Package name", 'Current version', 'Available version'))
    #write content to file
    for row, curren_patch in enumerate(contenr):
        sheet.write_row(row=row+2, col=0, data=curren_patch, cell_format=format['format_border'])
        csv_writer.writerow((curren_patch))
        if kernel_update == "no":
            if curren_patch[0].startswith("kernel") or curren_patch[0].startswith("linux-image"):
                kernel_update = reboot_require = 'yes'
                format_kernel = format_reboot = format['format_red']
        if reboot_require == "no":
            for current_package in packages_which_require_reboot:
                if str(curren_patch[0]).startswith(current_package) or curren_patch[0].find(
                        '-firmware-') != -1:
                    reboot_require = 'yes'
                    format_reboot = format['format_red']
                    break
    #write results to total sheet
    total_sheet.write(idx_glob + 2, 3, kernel_update, format_kernel)
    total_sheet.write(idx_glob + 2, 4, reboot_require, format_reboot)
    if counter>0:
        need_patching+=1; servers_for_patching.append(sheet.get_name())
        #determine columns width
        column_width=[]
        for c in range(3):
            column_width.append(max(len(current_patch_name[c]) for current_patch_name in contenr))
        #set columns width
        for c in range(3):
            sheet.set_column(c, c, width=column_width[c])
    else:
        not_need_patching+=1
    write_to_total_sheet(counter, "security ", sheet, total_sheet, format, idx_glob, "rhel_oracle")
    write_csv_total("./rhel_based/total.txt", sheet.get_name().lower(), kernel_update, reboot_require, counter, column_width)

def find_error(ssh_connection, std_error, std_stdout, sheet, idx_glob):
    '''Function for find error from error_list variable, return True if error found'''
    global error_count
    std_error_1 = std_error.read().decode()
    #    std_stdout_1= std_stdout.read().decode()
    for error in error_list.keys():
        if std_error_1.find(error) != -1 or std_stdout.find(error) != -1:
            print("Critical error with server", termcolor.colored(sheet.get_name() + '.', color='red'),
                  error_list[error])
            logging.warning("Critical error with server: {error}".format(error=error_list[error]))
            error_count += 1
            write_to_total_sheet(error_list[error], "error", sheet, total_sheet, format, idx_glob, 'rhel_oracle')
            ssh_connection.close()
            return True
    return False

def main():
    '''main function'''
    #open file and create list of servers
    global servers_for_patching
    server_list_file = open('server_list.txt', 'r')
    server_list = server_list_file.read().rstrip().split('\n')
    server_list_file.close()
    if args.nocheck=="yes":
        logging.info("Create csv-files only...")
        servers_for_patching=server_list
        perform_additional_actions(args, today, 'redhat_oracle', xlsx_name, settings, servers_for_patching)
        exit()
    #set ssh connection settings
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
    logging.info("Server's list: {servers}".format(servers=" ".join(server_list)))
    #looping servers
    for idx_glob, server in enumerate(server_list):
        logging.info("Working with {server} server...".format(server=server))
        print(termcolor.colored(
            server + "({idx_glob}/{servers_count})".format(idx_glob=idx_glob + 1, servers_count=servers_count),
            color='grey', on_color='on_green'))
        patches = []
        #add sheet with server_name
        try:
            sheet = xls_file.add_worksheet(str(server))
        except Exception:
            print("Error during creation xlsx-sheet for " + termcolor.colored(server, "red") + '. Server exists two or more time in file? ')
            continue
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
            logging.warning("Connevtion troubles with {server} server".format(server=server))
            write_to_total_sheet("Conection troubles", "error", sheet, total_sheet, format, idx_glob, 'rhel_oracle')
            error_count += 1
            continue
        except (paramiko.ssh_exception.AuthenticationException, paramiko.BadHostKeyException):
            print("Troubles with aouthorization on the server  " + termcolor.colored(server, "red") + ".")
            logging.warning("Troubles with aouthorization with {server} server".format(server=server))
            write_to_total_sheet("Authorization error", "error", sheet, total_sheet, format, idx_glob, 'rhel_oracle')
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
                logging.warning("There are error with patch: " + str(current_patch))
                continue
            try:
                number_position = re.search("-\d", current_patch_split[2])
                # id first correct element!=idx
                counter_2 += 1
                if not number_position:
                    print(termcolor.colored("Warning: ", color="yellow",
                                            on_color="on_grey") + "There are error with patch: " + str(current_patch))
                    logging.warning("There are error with patch: " + str(current_patch))
                    counter_2 -= 1
                    continue
            # if patch does not exists (current_patch_split[2])
            except IndexError:
                print(termcolor.colored("Warning: ", color="yellow",
                                        on_color="on_grey") + "There are error with patch: " + str(current_patch))
                logging.warning("There are error with patch: " + str(current_patch))
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
                                    patches.append([previous_patch_for_write[2][
                                                    :re.search("-\d", previous_patch_for_write[2]).start()],
                                                    current_rpm[
                                                    re.search("-\d", previous_patch_for_write[2]).start() + 1:],
                                                    previous_patch_for_write[2][
                                                    re.search("-\d", previous_patch_for_write[2]).start() + 1:]])
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
                            logging.warning("There are error with patch: " + str(current_patch))
                # if last element
                if idx == len(patches_list) - 1:
                    if previous_patch_for_write ==["", "", "", ""]:
                        previous_patch_for_write=current_patch_split
                    for current_rpm in all_rpm_list:
                        try:
                            if current_rpm[:number_position.start()] == current_patch_split[2][
                                                                        :number_position.start()] and \
                                current_rpm[number_position.start() + 1:][0].isdigit():
                                patches.append([previous_patch_for_write[2][
                                                :re.search("-\d", previous_patch_for_write[2]).start()],
                                                current_rpm[
                                                re.search("-\d", previous_patch_for_write[2]).start() + 1:],
                                                previous_patch_for_write[2][
                                                re.search("-\d", previous_patch_for_write[2]).start() + 1:]])
                                counter += 1
                                break
                        except IndexError:
                            pass
        write_to_file(patches, sheet, idx_glob, counter)

    add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format)
    xls_file.close()
    perform_additional_actions(args, today, 'redhat_oracle', xlsx_name, settings, servers_for_patching)


termcolor.cprint(
    "              .-. \n        .-'``(|||) \n     ,`\ \    `-`.               88                         88 \n    /   \ '``-.   `              88                         88 \n  .-.  ,       `___:    88   88  88,888,  88   88  ,88888, 88888  88   88 \n (:::) :        ___     88   88  88   88  88   88  88   88  88    88   88 \n  `-`  `       ,   :    88   88  88   88  88   88  88   88  88    88   88 \n    \   / ,..-`   ,     88   88  88   88  88   88  88   88  88    88   88 \n     `./ /    .-.`      '88888'  '88888'  '88888'  88   88  '8888 '88888' \n       `-..-(   ) \n              `-` ",
    "yellow", "on_grey")
# .*-firmware-*
packages_which_require_reboot = ("glibc", "hal", "systemd", "udev")


xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)
main()
