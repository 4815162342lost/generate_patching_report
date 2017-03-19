#!/usr/bin/python3
import sys
from distutils.sysconfig import get_python_lib
sys.path.append(get_python_lib())
import os
import json
import xlsxwriter
import subprocess
import datetime
import calendar

os.chdir(os.path.dirname(os.path.realpath(__file__)))

#get_file_name
month=datetime.datetime.now().month+1
xlsx_name=str(calendar.month_abbr[month])+"_full_patches.xlsx"

#counter for chart
need_patching = not_need_patching = error_count = 0

print("Starting the collect of all patches on the servers from  server_list.txt file...")

#errors list
error_list={'No minions matched the target':'The server is not connected to our server via salt',
            'Minion did not return':'Minion service is dead or server is not available',
            'is not available' : 'Module pkg.list_upgrades is not available'}

xls_file=xlsxwriter.Workbook(xlsx_name)

#create write cell formats
format_red=xls_file.add_format()
format_red.set_bg_color("#ffa7a7")
format_green=xls_file.add_format()
format_green.set_bg_color("#96d67c")
format_purple=xls_file.add_format()
format_purple.set_bg_color("#d195ec")
format_bold=xls_file.add_format()
format_bold.set_bold()
format_border=xls_file.add_format()

formats=(format_red, format_green, format_purple, format_bold, format_border)

for current_format in formats:
    current_format.set_border(1)

#create total sheet
total_sheet=xls_file.add_worksheet("Total")
total_sheet.set_tab_color("yellow")
total_sheet.write(0, 0, "Summary results:", format_bold)
total_sheet.set_column(0, 0, width=20)
total_sheet.set_column(1, 1, width=45)
total_sheet.write(1, 0, "Server name", format_bold)
total_sheet.write(1, 1, "Conclusion", format_bold)


def create_xlsx_legend():
    """Add legend to total sheet"""
    total_sheet.write(1, 5, "Conventions and stats:", format_bold)
    total_sheet.set_column(5, 5, width=30)
    total_sheet.set_column(6, 6, width=10)
    total_sheet.write(2, 5, "Patching is not required:", format_green)
    total_sheet.write(3, 5, "Server needs to patching:", format_red)
    total_sheet.write(4, 5, "There are problem with the server:", format_purple)

def add_chart(need_patching, not_need_patching, error_count):
    chart = xls_file.add_chart({'type': 'pie'})
    total_sheet.write(3, 6, need_patching, format_border)
    total_sheet.write(2, 6, not_need_patching, format_border)
    total_sheet.write(4, 6, error_count, format_border)

    chart.set_title({"name" : "The raw statistic"})
    chart.add_series({
        'categories': '=Total!$F$3:$F$5',
        'values': '=Total!$G$3:$G$5',
        'points': [
            {'fill': {'color': '#79eca3'}},
            {'fill': {'color': '#FF7373'}},
            {'fill': {'color': '#cb87fb'}},
        ],
    })
    total_sheet.insert_chart('F10', chart)

def write_to_excel_file(content, sheet_name, conten_type):
    """Function to write content to xlsx-file"""
    global idx; global need_patching; global not_need_patching; global error_count
    column0_width = 0
    column1_width = 0
    sheet = xls_file.add_worksheet(sheet_name)
    if conten_type=="patches":
        counter = 0
        for key, value in sorted(content[sheet_name].items()):
            if len(key)>column0_width:
                column0_width=len(key)
            if len(value)>column1_width:
                column1_width=len(value)
            sheet.write(counter + 2, 0, key, format_border)
            sheet.write(counter + 2, 1, value, format_border)
            counter += 1
        sheet.set_column(0, 0, width=column0_width+2)
        sheet.set_column(0, 1, width=column1_width+2)
        #if patching is not required
        if counter == 0:
            not_need_patching+=1
            sheet.set_column(0, 0, width=50)
            sheet.set_tab_color("#79eca3")
            sheet.write(0, 0, "All packages are up to date. Upgrade is not required", format_bold)
            total_sheet.write(idx + 2, 1, "All packages are up to date. Upgrade is not required", format_green)
            total_sheet.write(idx + 2, 0, str(sheet_name), format_green)
        #if only one patch required
        elif counter == 1:
            need_patching+=1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, "Only 1 package need to upgrade", format_bold)
            sheet.write(1, 0, "Package name", format_bold)
            sheet.write(1, 1, "Available version", format_bold)
            total_sheet.write(idx + 2, 1, "Only 1 package need to upgrade", format_red)
            total_sheet.write(idx + 2, 0, str(sheet_name), format_red)
        #more one patch required
        else:
            need_patching+=1
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(counter) + " packages need to upgrade", format_bold)
            sheet.write(1, 0, "Package name", format_bold)
            sheet.write(1, 1, "Available version", format_bold)
            total_sheet.write(idx + 2, 1, str(counter) + " packages need to upgrade", format_red)
            total_sheet.write(idx + 2, 0, str(sheet_name), format_red)
    if conten_type=="error":
        error_count+=1
        sheet.set_tab_color("#cb87fb")
        sheet.set_column(0, 0, 45)
        sheet.write(0, 0, error_list[error], format_bold)
        total_sheet.write(idx + 2, 1, error_list[error], format_purple)
        total_sheet.write(idx + 2, 0, str(sheet_name), format_purple)
    print(str(round((idx + 1) / servers_count * 100, 2)) + '% done (' + str(idx + 1) + "/" + str(servers_count) + ")")

with open("server_list.txt", "r") as server_list:
    #get server count for print statistic
    servers_count=server_list.read().count("\n")
    server_list.seek(0)
    for idx, current_server in enumerate(server_list):
        current_server=current_server.rstrip()
        need_pass=False
        print("Working with the server " + current_server)
        try:
            proc=subprocess.Popen("salt " + current_server + " pkg.list_upgrades refresh=True --output=json", shell=True, stdout=subprocess.PIPE, universal_newlines=True)
            proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            print("There are problem on the server " + current_server + ". Check the server now, it is urgent! You must kill the minion job on the server! ")
            continue
        proc_out=proc.stdout.read()
        #search errors in proc_our
        for error in error_list.keys():
            if proc_out.find(error) != -1:
                print("Server " + current_server + " return error: " + error_list[error])
                write_to_excel_file(error_list[error], current_server, "error")
                need_pass=True
                break
        #if errors not found
        if not need_pass:
            try:
                js = json.loads(proc_out)
            except:
                print("There are problem with json.loads command. Please, check manually the server" + current_server)
                write_to_excel_file("There are problem with json.loads command, current_server.rstrip()", "error")
                continue
            write_to_excel_file(js, current_server, "patches")

create_xlsx_legend()
add_chart(need_patching, not_need_patching, error_count)
xls_file.close()
print("All done. Please, use see the file " + xlsx_name + ".")
