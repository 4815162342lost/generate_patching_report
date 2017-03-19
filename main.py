#!/usr/bin/python3
import sys
from distutils.sysconfig import get_python_lib
sys.path.append(get_python_lib())
import os
import json
import xlsxwriter
import subprocess

print("Starting the collect of all patches on the servers from  server_list.txt file...")

error_list={'No minions matched the target':'The server is not connected to our server via salt',
            'Minion did not return':'Minion service is dead or server is not available'}

xls_file=xlsxwriter.Workbook("Full_patches_list.xlsx")

format_red=xls_file.add_format()
format_red.set_bg_color("#ffa7a7")
format_green=xls_file.add_format()
format_green.set_bg_color("#96d67c")
format_purple=xls_file.add_format()
format_purple.set_bg_color("#d195ec")
format_bold=xls_file.add_format()
format_bold.set_bold()

total_sheet=xls_file.add_worksheet("Total")
total_sheet.set_tab_color("yellow")
total_sheet.write(0,0, "Summary results:", format_bold)
total_sheet.set_column(0, 0, width=20)
total_sheet.set_column(1, 1, width=42)

def write_to_excel_file(content, sheet_name, conten_type):
    """Function to write content to xlsx-file"""
    global idx
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
            sheet.write(counter + 1, 0, key)
            sheet.write(counter + 1, 1, value)
            counter += 1
        sheet.set_column(0, 0, width=column0_width+2)
        sheet.set_column(0, 1, width=column1_width+2)
        if counter == 0:
            sheet.set_tab_color("#79eca3")
            total_sheet.write("Upgrade is not required", format_bold)
            sheet.set_column(0, 0, 42)
            sheet.write(0, 0, "All packages are up to date. Upgrade is not required", format_bold)
            total_sheet.write(idx + 1, 1, "All packages are up to date. Upgrade is not required", format_green)
            total_sheet.write(idx + 1, 0, str(sheet_name), format_green)
        elif counter == 1:
            sheet.set_tab_color("#f4eb23")
            sheet.write(0, 0, "Only 1 package need to upgrade", format_bold)
            total_sheet.write(idx + 1, 1, "Only 1 package need to upgrade", format_red)
            total_sheet.write(idx + 1, 0, str(sheet_name), format_red)
        else:
            sheet.set_tab_color("#FF7373")
            sheet.write(0, 0, str(counter) + " packages need to upgrade", format_bold)
            total_sheet.write_string(idx + 1, 1, str(counter) + " packages need to upgrade", format_red)
            total_sheet.write(idx + 1, 0, str(sheet_name), format_red)
    if conten_type=="error":
        sheet.set_tab_color("#cb87fb")
        sheet.set_column(0, 0, 42)
        sheet.write(0, 0, error_list[error], format_bold)
        total_sheet.write(idx + 1, 1, error_list[error], format_purple)
        total_sheet.write(idx + 1, 0, str(sheet_name), format_purple)
    print(str((idx + 1) / servers_count * 100) + '% done (' + str(idx + 1) + "/" + str(servers_count) + ")")

with open("server_list.txt", "r") as server_list:
    servers_count=server_list.read().count("\n")
    server_list.seek(0)
    for idx, current_server in enumerate(server_list):
        current_server=current_server.rstrip()
        need_pass=False
        print("Working with the server " + current_server)
        try:
            proc=subprocess.Popen("salt " + current_server + " pkg.list_upgrades refresh=True --output=json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            print("There are problem on the server " + current_server + ". Check the server now, it is urgent! You must kill the minion job on the server! ")
            continue
        proc_out=proc.stdout.read()
        for error in error_list.keys():
            if proc_out.find(error) != -1:
                print("Server " + current_server + " return error: " + error_list[error])
                write_to_excel_file(error_list[error], current_server, "error")
                need_pass=True
                break
        if not need_pass:
            try:
                js = json.loads(proc_out)
            except:
                print("There are problem with json.loads command. Please, check manually the server" + current_server)
                write_to_excel_file("There are problem with json.loads command, current_server.rstrip()", "error")
                continue
            write_to_excel_file(js, current_server, "patches")
xls_file.close()
