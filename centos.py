#!/usr/bin/python3
import sys
from distutils.sysconfig import get_python_lib

sys.path.append(get_python_lib())
import os
import json
import xlsxwriter
import subprocess
import re
import termcolor
from auto_mm import *
from create_excel_template import *
from send_email import *
from main import *
os.chdir(os.path.dirname(os.path.realpath(__file__)))
from auto_mm import *

settings=get_settings()
args=parcer()

servers_for_patching = []

# get_file_name
today = datetime.datetime.now()

# counter for chart
need_patching = not_need_patching = error_count = 0

packages_which_require_reboot = ("glibc", "hal", "systemd", "udev")

def write_to_excel_file(content_updates_pkgs, content_all_pkgs, sheet_name, conten_type, idx):
    """Function to write content to xlsx-file"""
    global need_patching
    global not_need_patching
    global error_count
    kernel_update = reboot_require = "no"
    format_kernel = format_reboot = format['format_green']
    no_potential_risky_packages = "yes"
    format_potential_risky_packages = format['format_green']
    column0_width = column1_width = column2_width = 0
    try:
        sheet = xls_file.add_worksheet(sheet_name)
    except Exception as e:
        error_count += 1
        total_sheet.write(idx + 2, 1, "Can not create sheet", format['format_purple'])
        total_sheet.write(idx + 2, 2, "", format['format_bold'])
        total_sheet.write(idx + 2, 0, str(sheet_name), format['format_purple'])
        total_sheet.write(idx + 2, 3, "Unknown", format['format_purple'])
        total_sheet.write(idx + 2, 4, "Unknown", format['format_purple'])
        total_sheet.write(idx + 2, 5, "Unknown", format['format_purple'])
        termcolor.cprint(
            'Error occured during creation the sheet %s. Perhaps you have two or more same servers in server_list.txt file' % sheet_name,
            color='red', on_color='on_white')
        return None
    if conten_type == "patches":
        counter = 0
        # avoid the bug #41479 https://github.com/saltstack/salt/issues/41479
        try:
            content_updates_pkgs.pop("retcode")
            content_all_pkgs.pop("retcode")
        except KeyError:
            pass
        for key, value in sorted(content_updates_pkgs.items()):
            if len(key) > column0_width:
                column0_width = len(key)
            if len(str(value)) > column1_width:
                column1_width = len(value)
            # if new packages (dependence) will be installed with upgrade
            try:
                if len(str(content_all_pkgs[key])) > column2_width:
                    column2_width = len(str(content_all_pkgs[key]))
            except KeyError:
                pass
            if no_potential_risky_packages == "yes":
                for current_bad_package in settings['bad_packages']:
                    if str(key).startswith(current_bad_package):
                        no_potential_risky_packages = "no"
                        format_potential_risky_packages = format['format_red']
                        break
            if kernel_update == "no":
                if str(key).startswith("kernel") == True or str(key).startswith("linux-image") == True:
                    kernel_update = "yes"
                    format_kernel = format['format_red']
                    reboot_require = "yes"
                    format_reboot = format['format_red']
            sheet.write(counter + 2, 0, key, format['format_border'])
            try:
                sheet.write(counter + 2, 1, content_all_pkgs[key], format['format_border'])
            except KeyError:
                sheet.write(counter + 2, 1, "new packages (will be installed as dependency)", format['format_border'])
            sheet.write(counter + 2, 2, value, format['format_border'])
            counter += 1
        if kernel_update == "no":
            for current_package in packages_which_require_reboot:
                if current_package in content_updates_pkgs.keys():
                    reboot_require = "yes"
                    format_reboot = format['format_red']
                    break
            if reboot_require == "no":
                for current_package in content_updates_pkgs.keys():
                    if current_package.find("-firmware-") != -1:
                        reboot_require = "yes"
                        format_reboot = format['format_red']
                        break
        sheet.set_column(0, 0, width=column0_width + 2)
        sheet.set_column(1, 1, width=column1_width + 2)
        sheet.set_column(2, 2, width=column2_width + 2)
        # if patching is not required
        if counter == 0:
            not_need_patching += 1
            sheet.set_column(0, 0, width=50)
            sheet.set_tab_color("#79eca3")
            sheet.write(0, 0, "All packages are up to date. Upgrade is not required", format['format_bold'])
            total_sheet.write(idx + 2, 1, "All packages are up to date. Upgrade is not required", format['format_green'])
            total_sheet.write(idx + 2, 2, "", format['format_bold'])
            total_sheet.write(idx + 2, 3, kernel_update, format_kernel)
            total_sheet.write(idx + 2, 4, reboot_require, format_reboot)
            total_sheet.write(idx + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
            total_sheet.write(idx + 2, 0, str(sheet_name), format['format_green'])
        # if only one patch required
        elif counter == 1:
            servers_for_patching.append(sheet.get_name())
            need_patching += 1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, "Only 1 package need to upgrade", format['format_bold'])
            sheet.write(1, 0, "Package name", format['format_bold'])
            sheet.write(1, 1, "Current version", format['format_bold'])
            sheet.write(1, 2, "Available version", format['format_bold'])
            total_sheet.write(idx + 2, 1, "Only 1 package need to upgrade", format['format_red'])
            total_sheet.write(idx + 2, 2, "", format['format_bold'])
            total_sheet.write(idx + 2, 3, kernel_update, format_kernel)
            total_sheet.write(idx + 2, 4, reboot_require, format_reboot)
            total_sheet.write(idx + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
            total_sheet.write(idx + 2, 0, str(sheet_name), format['format_red'])
        # more one patch required
        else:
            servers_for_patching.append(sheet.get_name())
            need_patching += 1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(counter) + " packages need to upgrade", format['format_bold'])
            sheet.write(1, 0, "Package name", format['format_bold'])
            sheet.write(1, 1, "Current version", format['format_bold'])
            sheet.write(1, 2, "Available version", format['format_bold'])
            total_sheet.write(idx + 2, 2, "", format['format_bold'])
            total_sheet.write(idx + 2, 3, kernel_update, format_kernel)
            total_sheet.write(idx + 2, 4, reboot_require, format_reboot)
            total_sheet.write(idx + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
            total_sheet.write(idx + 2, 1, str(counter) + " packages need to upgrade", format['format_red'])
            total_sheet.write(idx + 2, 0, str(sheet_name), format['format_red'])
    if conten_type == "error":
        error_count += 1
        sheet.set_tab_color("#cb87fb")
        sheet.set_column(0, 0, 45)
        sheet.write(0, 0, "Fatal error", format['format_bold'])
        total_sheet.write(idx + 2, 1, "Fatal error", format['format_purple'])
        total_sheet.write(idx + 2, 2, "", format['format_bold'])
        total_sheet.write(idx + 2, 0, str(sheet_name), format['format_purple'])
        total_sheet.write(idx + 2, 3, "Unknown", format['format_purple'])
        total_sheet.write(idx + 2, 4, "Unknown", format['format_purple'])
        total_sheet.write(idx + 2, 5, "Unknown", format['format_purple'])


def main_function():
    file= open('./server_list.txt', 'r')
    server_list = open('./server_list.txt', 'r').read().rstrip().split('\n')
    file.close()

    print(','.join(server_list))

    try:
        proc_get_updates = subprocess.Popen("salt -L '" + ','.join(
            server_list) + "' pkg.list_upgrades refresh=True --output=json --static  --hide-timeout",
                                            shell=True, universal_newlines=True, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE)
        stdout_get_updates, stderr_get_updates = proc_get_updates.communicate(timeout=300)
        proc_get_all_pkgs = subprocess.Popen(
            "salt -L '" + ','.join(server_list) + "' pkg.list_pkgs --output=json --static  --hide-timeout",
            shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout_get_all_pkgs, stderr_get_all_pkgs = proc_get_all_pkgs.communicate(timeout=300)
    except subprocess.TimeoutExpired:
        proc_get_updates.kill()
        proc_get_all_pkgs.kill()
        print("There are problem with salt! ")
        os._exit(1)


    # avoid the bug #40311 https://github.com/saltstack/salt/issues/40311
    stdout_get_updates = re.sub("Minion .* did not respond. No job will be sent.", "", stdout_get_updates)
    stdout_get_updates = re.sub("No minions matched the target. No command was sent, no jid was assigned.", "",
                                stdout_get_updates)
    stdout_get_updates == re.sub("minion .* was already deleted from tracker, probably a duplicate key", "",
                                 stdout_get_updates)


    proc_out_get_updates_json = json.loads(stdout_get_updates)
    stdout_get_all_pkgs = re.sub("Minion .* did not respond. No job will be sent.", "", stdout_get_all_pkgs)
    stdout_get_all_pkgs = re.sub("No minions matched the target. No command was sent, no jid was assigned.", "",
                                 stdout_get_all_pkgs)
    stdout_get_all_pkgs = re.sub("minion .* was already deleted from tracker, probably a duplicate key", "",
                                 stdout_get_all_pkgs)
    proc_out_get_all_pkgs_json = json.loads(stdout_get_all_pkgs)

    print('Starting to create xlsx-file...')
    error_list_from_xlsx = []
    for idx, current_server in enumerate(server_list):
        try:
            write_to_excel_file(proc_out_get_updates_json[current_server], proc_out_get_all_pkgs_json[current_server],
                                current_server, "patches", idx)
        except KeyError:
            error_list_from_xlsx.append(current_server)
            write_to_excel_file(None, None, current_server, "error", idx)
    if error_list_from_xlsx:
        termcolor.cprint("There are problem with following servers:\n" + ',\n'.join(error_list_from_xlsx), color='red',
                         on_color='on_white')
    add_chart(need_patching, not_need_patching, error_count, xls_file, total_sheet, format)
    xls_file.close()
    if args.csv == 'yes' and servers_for_patching:
        error_list_from_csv = working_with_csv(servers_for_patching, db_cur, today, 'centos')
        if error_list_from_csv:
            termcolor.cprint("Maintenance mode will be incorrect:\n" + ',\n'.join(error_list_from_csv), color='magenta',
                             on_color='on_white')
        db_cur.close()
    if args.email != None:
        send_mail(args.email, settings['email_from'], settings['smtp_server'],  xlsx_name, today, 'Patching list for CentOS ')
        print("All done, the file \"{file_name}\" has been sent to e-mail {mail_address}".format(file_name=xlsx_name,
                                                                                                 mail_address=args.email))
    else:
        print("All done. Please, see the file \"" + xlsx_name + "\". Have a nice day!")


# get server list and raise main function
print("Hello! Nice to meet you!")
termcolor.cprint(
    ", // ,,/ ,.// ,/ ,// / /, // ,/, /, // ,/,\n/, // ,/,_|_// ,/ ,, ,/, // ,/ /, //, /,/\n /, /,.-'   '-. ,// ////, // ,/,/, // ///\n, ,/,/         \ // ,,///, // ,/,/, // ,\n,/ , ^^^^^|^^^^^ ,// ///  /,,/,/, ///, //\n / //     |  O    , // ,/, //, ///, // ,/\n,/ ,,     J\/|\_ |+'(` , |) ^ ||\|||\|/` |\n /,/         |   || ,)// |\/-\|| ||| |\] .\n/ /,,       /|    . ,  ///, . /, // ,//, /\n, / /,/     \ \    ). //, ,( ,/,/, // ,/,",
    color='blue', on_color='on_grey')
print("Starting to collect of all patches...")
xlsx_name = 'Unix_List_of_updates_' + str(today.strftime("%B_%Y")) + "_Centos.xlsx"
xls_file = xlsxwriter.Workbook(xlsx_name)
format=create_formats(xls_file)
total_sheet=create_total_sheet(xls_file, format)
create_xlsx_legend(total_sheet, format)
db_cur=sqlite(args.csv)
main_function()
