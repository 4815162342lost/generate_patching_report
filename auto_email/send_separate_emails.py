#!/usr/bin/python3
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
import sqlite3
import os
import xlsxwriter
import itertools
import sys
sys.path.append('./modules/')
from create_excel_template import *
import csv


def return_server_groups(server_list):
    server_groups={}
    for current_server in server_list:
        so=db_cur.execute("SELECT SERVER_OWNERS_EMAILS.SERVICE_OWNERS FROM SERVER_OWNERS_EMAILS\
                          INNER JOIN SERVERS ON SERVER_OWNERS_EMAILS.PROJECT_NAME=SERVERS.PROJECT\
                          WHERE SERVERS.SERVER_NAME=:server_name COLLATE NOCASE", {'server_name' : current_server}).fetchone()
        if so[0] not in server_groups:
            server_groups[so[0]]=[current_server]
        else:
            server_groups[so[0]].append(current_server)
    return server_groups

def prepare_xlsx_file(servers):
    xlsx_file=xlsxwriter.Workbook('/tmp/patching_list.xlsx')
    format = create_formats(xlsx_file)
    total_sheet=xlsx_file.add_worksheet("Total")
    for current_server in servers:
        server_sheet=xlsx_file.add_worksheet(current_server.upper())
        server_file_csv=csv.reader(open(current_server.lower(), 'r'), delimiter=';')
        #search patches count
        for row in csv_reader:
            if row[0]==current_server:
                patches_count=row[3]
                break
        if patches_count!=0:
            server_sheet.write(0,0, "{count} packages will be updated".format(count=patches_count))
            for idx, current_patch in enumerate(server_file_csv):
                server_sheet.write_row(idx+1, 0, current_patch)
        else:
            server_sheet.write(0, 0, "Upgade is not needed")
            return 0
    xlsx_file.close()
            #for current_string in itertools.islice(server_file.readlines(), 1):


def main():
    servers_list=os.listdir("./")
    servers_list.remove('total.txt')
    uniq_so_group_with_servers=return_server_groups(servers_list)
    for current_uniq_so_group_servers in uniq_so_group_with_servers.values():
        prepare_xlsx_file(current_uniq_so_group_servers)


db_cur=sqlite3.connect('./patching.db').cursor()
os.chdir(os.path.dirname(os.path.realpath(__file__))+'/rhel_based/')
csv_reader=csv.reader(open("./total.txt", 'r'), delimiter=';')
main()
