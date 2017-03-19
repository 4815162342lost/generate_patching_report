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
            'Minion did not return':'Minion service is dead or server is not available. Please, check the server or fix the server list'}

xls_file=xlsxwriter.Workbook("Full_patches_list.xlsx")
format=xls_file.add_format()
format.set_bg_color("red")

total_sheet=xls_file.add_worksheet("Total")
total_sheet.set_tab_color("yellow")
total_sheet.write(0,0, "Summary results:")

def write_to_excel_file(content, sheet_name):
    """Function to write content to xlsx-file"""
    if sheet_name!="total_sheet":
        sheet = xls_file.add_worksheet(current_server)
        
        




with open("server_list.txt", "r") as server_list:
    servers_count=server_list.read().count("\n")
    server_list.seek(0)
    for idx, current_server in enumerate(server_list):
        need_pass=False
        print("Working with the server " + current_server.rstrip())
        sheet=xls_file.add_worksheet(current_server)
        try:
            proc=subprocess.Popen("salt " + current_server.rstrip() + " pkg.list_upgrades refresh=True --output=json", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            proc.wait(timeout=300)
        except subprocess.TimeoutExpired:
            print("There are problem on the server " + current_server + ". Check the server now, it is urgent! You must kill the minion job on the server! ")
            break
#        except:
#            print("There are problem with json.loads command. Please, check manually")
#            break
        proc_out= proc.stdout.read()
        for error in error_list.keys():
            if proc_out.find(error) != -1:
                print("Server " + current_server + " return error: " + error_list[error])
                sheet.write(0, 0, error_list[error])
                need_pass=True
                break

        js = json.loads(proc_out)
        counter=0
        for  key, value in sorted(js[current_server.strip()].items()):
            sheet.write(counter+1, 0, key)
            sheet.write(counter+1, 1, value)
            counter+=1
        if counter==0:
            sheet.set_tab_color("green")
            total_sheet.write("Upgrade is not required")
            sheet.write(0, 0, "All packages are up to date. Upgrade is not required")
            total_sheet.write(idx+1, 1, "All packages are up to date. Upgrade is not required")
        elif counter==1:
            sheet.set_tab_color("red")
            sheet.write(0, 0, "Only 1 package need to upgrade")
            total_sheet.write(idx+1, 1, "Only 1 package need to upgrade")
        else:
            sheet.set_tab_color("red")
            sheet.write(0, 0, str(counter)+ " packages need to upgrade")
            total_sheet.set_column(0, 0, width=20, cell_format=format)
            total_sheet.write(idx+1, 1, str(counter) + " packages need to upgrade", format)
        total_sheet.write(1, 0, current_server.rstrip())
        print(str((idx+1)/servers_count*100) + '% done (' + str(idx+1) + "/" + str(servers_count) + ")")
xls_file.close()
