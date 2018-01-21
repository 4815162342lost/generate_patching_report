#!/usr/bin/python3
import sys
from distutils.sysconfig import get_python_lib

sys.path.append(get_python_lib())
import os
import json
import xlsxwriter
import subprocess
import re
import argparse
import sqlite3
import termcolor

os.chdir(os.path.dirname(os.path.realpath(__file__)))
import sys

sys.path.insert(0, './auto_mm.py/')

from auto_mm import *

# .*-firmware-*
# confidential data
packages_which_require_reboot = ("glibc", "hal", "systemd", "udev")
bad_packages = ('nano', 'vi')
smtp_server = 'smtp.my_organization.net'
email_from = "me"

servers_for_patching = []

# create parser for working with script input options
parser = argparse.ArgumentParser()
parser.add_argument("-e", "--email", type=str, required=False, help="Enter your e-mail")
parser.add_argument("-s", "--source", type=str, required=False, default='file',
                    help="read servers from server_list.txt file or database ('file' ot 'db', default -- from file)")
parser.add_argument("-c", "--csv", type=str, required=False, default='no',
                    help="create csv-file with maintenance mode schedule or not ('yes' or 'no'), default -- 'no'")
args = parser.parse_args()

# get_file_name
today = datetime.datetime.now()
xlsx_name = 'linux_list_of_updates_' + str(today.strftime("%B_%Y")) + "_CentOS.xlsx"

# counter for chart
need_patching = not_need_patching = error_count = 0

print("Hello! Nice to meet you!")
termcolor.cprint(
    ", // ,,/ ,.// ,/ ,// / /, // ,/, /, // ,/,\n/, // ,/,_|_// ,/ ,, ,/, // ,/ /, //, /,/\n /, /,.-'   '-. ,// ////, // ,/,/, // ///\n, ,/,/         \ // ,,///, // ,/,/, // ,\n,/ , ^^^^^|^^^^^ ,// ///  /,,/,/, ///, //\n / //     |  O    , // ,/, //, ///, // ,/\n,/ ,,     J\/|\_ |+'(` , |) ^ ||\|||\|/` |\n /,/         |   || ,)// |\/-\|| ||| |\] .\n/ /,,       /|    . ,  ///, . /, // ,//, /\n, / /,/     \ \    ). //, ,( ,/,/, // ,/,",
    color='blue', on_color='on_grey')
print("Starting to collect of all patches...")

xls_file = xlsxwriter.Workbook(xlsx_name)

# create different formats for excel-file
format_red = xls_file.add_format()
format_red.set_bg_color("#ffa7a7")
format_green = xls_file.add_format()
format_green.set_bg_color("#96d67c")
format_purple = xls_file.add_format()
format_purple.set_bg_color("#d195ec")
format_bold = xls_file.add_format()
format_yellow = xls_file.add_format()
format_yellow.set_bg_color("fff620")
format_gray = xls_file.add_format()
format_gray.set_bg_color("#a3a3a3")
format_blue = xls_file.add_format()
format_blue.set_bg_color("#87cad8")
format_bold.set_bold()
format_border = xls_file.add_format()
format_kernel = xls_file.add_format()
format_reboot = xls_file.add_format()
format_potential_risky_packages = xls_file.add_format()

formats = (format_red, format_green, format_purple, format_yellow, format_gray, format_blue, format_bold, format_border,
           format_kernel, format_reboot, format_potential_risky_packages)
column_width = (20, 45, 51, 14, 16, 34)

# set border 1 for all formats
for current_format in formats:
    current_format.set_border(1)

# create total sheet
total_sheet = xls_file.add_worksheet("Total")
total_sheet.set_tab_color("yellow")
total_sheet.write(0, 0, "Summary results:", format_bold)

# select width for columns
for idx in range(0, 6):
    total_sheet.set_column(idx, idx, width=column_width[idx])

total_sheet.write(1, 0, "Server name", format_bold)
total_sheet.write(1, 1, "Conclusion", format_bold)
total_sheet.write(1, 2, "Cycle results(fully patches or state the issue occurred)", format_bold)
total_sheet.write(1, 3, "Kernel update", format_bold)
total_sheet.write(1, 4, "Reboot required", format_bold)
total_sheet.write(1, 5, "All potential risky updates excluded", format_bold)


def create_xlsx_legend():
    """Add legend to total sheet"""
    total_sheet.write(1, 7, "Conventions and stats:", format_bold)
    total_sheet.set_column(7, 7, width=30)
    total_sheet.set_column(8, 8, width=12)
    total_sheet.write(2, 7, "Patching is not required", format_green)
    total_sheet.write(3, 7, "Server needs patching", format_red)
    total_sheet.write(4, 7, "There are problem with the server", format_purple)
    total_sheet.write(5, 7, "Updates installed successfully", format_yellow)
    total_sheet.write(6, 7, "Updates failed", format_gray)
    total_sheet.write(7, 7, "Excluded from patching", format_blue)
    total_sheet.write(1, 7, "Server count", format_bold)


def add_chart(need_patching, not_need_patching, error_count):
    """Add chart"""
    chart_before_patching = xls_file.add_chart({'type': 'pie'})
    total_sheet.write(3, 8, need_patching, format_border)
    total_sheet.write(2, 8, not_need_patching, format_border)
    total_sheet.write(4, 8, error_count, format_border)
    total_sheet.write(5, 8, "n/a", format_border)
    total_sheet.write_formula(6, 8, "=SUM(I3:I5)-(I6+I8)", format_border)
    total_sheet.write(7, 8, "n/a", format_border)

    chart_before_patching.set_title({"name": "The raw statistic (before patching)"})
    chart_before_patching.add_series({
        'categories': '=Total!$H$3:$H$5',
        'values': '=Total!$I$3:$I$5',
        'points': [
            {'fill': {'color': '#79eca3'}},
            {'fill': {'color': '#FF7373'}},
            {'fill': {'color': '#cb87fb'}},
        ],
    })
    total_sheet.insert_chart('H10', chart_before_patching)

    chart_after_patching = xls_file.add_chart({"type": "pie"})
    chart_after_patching.set_title({"name": "Patching results"})
    chart_after_patching.add_series({
        'categories': '=Total!$H$6:$H$8',
        'values': '=Total!$I$6:$I$8',
        'points': [
            {'fill': {'color': "#fff620"}},
            {'fill': {'color': "#a3a3a3"}},
            {'fill': {'color': "#87cad8"}},
        ],
    })
    total_sheet.insert_chart('H28', chart_after_patching)


def write_to_excel_file(content_updates_pkgs, content_all_pkgs, sheet_name, conten_type, idx):
    """Function to write content to xlsx-file"""
    global need_patching
    global not_need_patching
    global error_count
    kernel_update = reboot_require = "no"
    format_kernel = format_reboot = format_green
    no_potential_risky_packages = "yes"
    format_potential_risky_packages = format_green
    column0_width = column1_width = column2_width = 0
    try:
        sheet = xls_file.add_worksheet(sheet_name)
    except Exception as e:
        error_count += 1
        total_sheet.write(idx + 2, 1, "Can not create sheet", format_purple)
        total_sheet.write(idx + 2, 2, "", format_bold)
        total_sheet.write(idx + 2, 0, str(sheet_name), format_purple)
        total_sheet.write(idx + 2, 3, "Unknown", format_purple)
        total_sheet.write(idx + 2, 4, "Unknown", format_purple)
        total_sheet.write(idx + 2, 5, "Unknown", format_purple)
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
                for current_bad_package in bad_packages:
                    if str(key).startswith(current_bad_package):
                        no_potential_risky_packages = "no"
                        format_potential_risky_packages = format_red
                        break
            if kernel_update == "no":
                if str(key).startswith("kernel") == True or str(key).startswith("linux-image") == True:
                    kernel_update = "yes"
                    format_kernel = format_red
                    reboot_require = "yes"
                    format_reboot = format_red
            sheet.write(counter + 2, 0, key, format_border)
            try:
                sheet.write(counter + 2, 1, content_all_pkgs[key], format_border)
            except KeyError:
                sheet.write(counter + 2, 1, "new packages (will be installed as dependency)", format_border)
            sheet.write(counter + 2, 2, value, format_border)
            counter += 1
        if kernel_update == "no":
            for current_package in packages_which_require_reboot:
                if current_package in content_updates_pkgs.keys():
                    reboot_require = "yes"
                    format_reboot = format_red
                    break
            if reboot_require == "no":
                for current_package in content_updates_pkgs.keys():
                    if current_package.find("-firmware-") != -1:
                        reboot_require = "yes"
                        format_reboot = format_red
                        break
        sheet.set_column(0, 0, width=column0_width + 2)
        sheet.set_column(1, 1, width=column1_width + 2)
        sheet.set_column(2, 2, width=column2_width + 2)
        # if patching is not required
        if counter == 0:
            not_need_patching += 1
            sheet.set_column(0, 0, width=50)
            sheet.set_tab_color("#79eca3")
            sheet.write(0, 0, "All packages are up to date. Upgrade is not required", format_bold)
            total_sheet.write(idx + 2, 1, "All packages are up to date. Upgrade is not required", format_green)
            total_sheet.write(idx + 2, 2, "", format_bold)
            total_sheet.write(idx + 2, 3, kernel_update, format_kernel)
            total_sheet.write(idx + 2, 4, reboot_require, format_reboot)
            total_sheet.write(idx + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
            total_sheet.write(idx + 2, 0, str(sheet_name), format_green)
        # if only one patch required
        elif counter == 1:
            servers_for_patching.append(sheet.get_name())
            need_patching += 1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, "Only 1 package need to upgrade", format_bold)
            sheet.write(1, 0, "Package name", format_bold)
            sheet.write(1, 1, "Current version", format_bold)
            sheet.write(1, 2, "Available version", format_bold)
            total_sheet.write(idx + 2, 1, "Only 1 package need to upgrade", format_red)
            total_sheet.write(idx + 2, 2, "", format_bold)
            total_sheet.write(idx + 2, 3, kernel_update, format_kernel)
            total_sheet.write(idx + 2, 4, reboot_require, format_reboot)
            total_sheet.write(idx + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
            total_sheet.write(idx + 2, 0, str(sheet_name), format_red)
        # more one patch required
        else:
            servers_for_patching.append(sheet.get_name())
            need_patching += 1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(counter) + " packages need to upgrade", format_bold)
            sheet.write(1, 0, "Package name", format_bold)
            sheet.write(1, 1, "Current version", format_bold)
            sheet.write(1, 2, "Available version", format_bold)
            total_sheet.write(idx + 2, 2, "", format_bold)
            total_sheet.write(idx + 2, 3, kernel_update, format_kernel)
            total_sheet.write(idx + 2, 4, reboot_require, format_reboot)
            total_sheet.write(idx + 2, 5, no_potential_risky_packages, format_potential_risky_packages)
            total_sheet.write(idx + 2, 1, str(counter) + " packages need to upgrade", format_red)
            total_sheet.write(idx + 2, 0, str(sheet_name), format_red)
    if conten_type == "error":
        error_count += 1
        sheet.set_tab_color("#cb87fb")
        sheet.set_column(0, 0, 45)
        sheet.write(0, 0, "Fatal error", format_bold)
        total_sheet.write(idx + 2, 1, "Fatal error", format_purple)
        total_sheet.write(idx + 2, 2, "", format_bold)
        total_sheet.write(idx + 2, 0, str(sheet_name), format_purple)
        total_sheet.write(idx + 2, 3, "Unknown", format_purple)
        total_sheet.write(idx + 2, 4, "Unknown", format_purple)
        total_sheet.write(idx + 2, 5, "Unknown", format_purple)


def send_mail(email_adr, filename):
    '''Function for send e-mail'''
    import smtplib
    from email.mime.base import MIMEBase
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email import encoders
    import io
    attachment_text = str("Full patching list for " + today.strftime("%B"))
    msg = MIMEMultipart()
    msg['Subject'] = 'Patching_list'
    msg['From'] = email_from
    msg['To'] = email_adr
    f = io.StringIO(attachment_text)
    part = MIMEText(f.getvalue())
    msg.attach(part)
    part = MIMEBase('application', "octet-stream")
    part.set_payload(open(filename, "rb").read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', 'attachment', filename=filename)
    msg.attach(part)
    try:
        s = smtplib.SMTP(smtp_server)
        s.sendmail(msg['From'], msg['To'], msg.as_string())
        s.quit()
    except Exception as e:
        termcolor.cprint('Error occured during sendig e-mail. Exception: ', color='red', on_color='on_white')
        print(e)

        
def get_server_list():
    '''Function for read servers which shoul be patched from server_list.txt file or patching.db database'''
    if args.source == 'file':
        server_list_file = open('server_list.txt', 'r')
        server_list = server_list_file.read().rstrip().split('\n')
        server_list_file.close()
    elif args.source == 'db':
        server_list_db = db_cur.execute("SELECT SERVER_NAME FROM SERVERS\
                                          WHERE OS='centos'").fetchall()
        server_list = list(str(current_server[0]) for current_server in server_list_db)
    else:
        print("--source option is incorrect!")
        exit(1)
    return server_list


def working_with_csv():
    '''Function for raise other function with csv-creation from auto_mm.py file'''
    servers_for_write_to_csv, servers_with_additional_monitors, error_list_from_csv = create_csv_list_with_servers_for_write_and_with_additional_monitors(
        servers_for_patching, db_cur, today)
    write_to_csv('linux_MM_{date}_patching_CentOS'.format(date=today.strftime("%b_%Y")), servers_for_write_to_csv)
    print('Hey, csv-file linux_MM_{date}_patching_CentOS.csv has been compiled!'.format(date=today.strftime("%b_%Y")))
    if servers_with_additional_monitors:
        write_to_csv('linux_MM_CIS_{date}_patching_CentOS'.format(date=today.strftime("%b_%Y")),
                     servers_with_additional_monitors)
        print("FYI: csv-file linux_MM_CIS_{date}_patching_CentOS.csv created!".format(date=today.strftime("%b_%Y")))
    return error_list_from_csv


def main_function(server_list):
    '''main function: call salt, call function for write to excel or csv with maintenance mode, call function with e-mail sending'''
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
    # end common operations with excel-file
    create_xlsx_legend()
    add_chart(need_patching, not_need_patching, error_count)
    xls_file.close()

    if args.csv == 'yes' and servers_for_patching:
        error_list_from_csv = working_with_csv()
        if error_list_from_csv:
            termcolor.cprint("Maintenance mode will be incorrect:\n" + ',\n'.join(error_list_from_csv), color='magenta',
                             on_color='on_white')
    try:
        db_cur.close()
    except NameError:
        pass
    if args.email != None:
        send_mail(args.email, xlsx_name)
        print("All done, the file \"{file_name}\" has been sent to e-mail {mail_address}".format(file_name=xlsx_name,
                                                                                                 mail_address=args.email))
    else:
        print("All done. Please, see the file \"" + xlsx_name + "\". Have a nice day!")


if args.source == 'db' or args.csv == 'yes':
    # open database or not
    db_con = sqlite3.connect('./auto_mm.py/patching.db')
    db_cur = db_con.cursor()

# get server list and raise main function
main_function(get_server_list())
