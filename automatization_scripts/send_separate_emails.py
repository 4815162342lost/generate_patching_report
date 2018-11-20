#!/usr/bin/python3
import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from email.mime.image import MIMEImage
import sqlite3
import os
import xlsxwriter
import termcolor
import sys
sys.path.append('./modules/')
from create_excel_template import *
import csv
import datetime
import configparser

def get_settings():
    '''parse the config file'''
    parse_conf=configparser.ConfigParser()
    parse_conf.read("./settings.cfg")
    return parse_conf['auto_e_mail_separate_to_so_with_pacthing_list']


def return_server_groups(server_list):
    '''return the dict which contain service owner and servers'''
    server_groups={}
    for current_server in server_list:
        so=db_cur.execute("SELECT SERVER_OWNERS_EMAILS.SERVICE_OWNERS FROM SERVER_OWNERS_EMAILS\
                          INNER JOIN SERVERS ON SERVER_OWNERS_EMAILS.PROJECT_NAME=SERVERS.PROJECT\
                          WHERE SERVERS.SERVER_NAME=:server_name COLLATE NOCASE", {'server_name' : current_server}).fetchone()
        #if new key -- create them, if old -- only append new value
        if so[0] not in server_groups:
            server_groups[so[0]]=[current_server]
        else:
            server_groups[so[0]].append(current_server)
    #example: {'Faith Connor,Zoey Coatcher': ['cent_os', 'secret_server'], 'Lous Coatcher,Our_team': ['server22']}
    return server_groups

def prepare_xlsx_file(servers):
    '''Function for generate xlsx-files and write them to /tmp/ directory, servers -- list of servers'''
    #change the position in file to beginning
    csv_file.seek(0)
    #create xsls-file, total_sheet and get formats
    xlsx_file=xlsxwriter.Workbook('/tmp/patching_list.xlsx')
    format = create_formats(xlsx_file)
    total_sheet=xlsx_file.add_worksheet("Total")
    total_sheet.set_tab_color(color="yellow")
    total_sheet.write_row(row=0, col=0,data=("Server name", "Conclusion", "Kernel upgrade", "Reboot required"), cell_format=format['format_bold'])
    for idx, current_server in enumerate(servers):
        #crete sheet with server name and open txt-file with server
        server_sheet=xlsx_file.add_worksheet(current_server.upper())
        server_file_csv=csv.reader(open(current_server.lower(), 'r'), delimiter=';')
        #extract the line which related with current server from total.txt file, save this line to patches_str variable
        for row in csv_reader:
            if row[0]==current_server:
                patches_str=row;
                break
        #write the patches to xlsx-sheet and set width
        if int(patches_str[3])!=0:
            server_sheet.write(0,0, "{count} packages will be updated".format(count=patches_str[3]), format['format_bold'])
            server_sheet.write_row(1, 0, next(server_file_csv)[0:3], cell_format=format['format_bold'])
            for idx1, current_patch in enumerate(server_file_csv):
                server_sheet.write_row(idx1+2, 0, current_patch, cell_format=format['format_border'])
            for current_width in range(4, 7):
                server_sheet.set_column(current_width - 4, current_width - 4, width=int(patches_str[current_width]))
            server_sheet.set_tab_color(color="red")
            total_sheet.write_row(row=idx+1, col=0,data=(current_server.upper(), "{count} packages need to update".format(count=patches_str[3]), patches_str[1], patches_str[2]), cell_format=format['format_red'])
            total_sheet.write_url(row=idx + 1, col=0, url="internal:'{sheet_name}'!A1".format(sheet_name=current_server.upper()),cell_format=format['format_red_url'], string=current_server.upper())
        else:
            server_sheet.write(0, 0, "Upgrade is not needed", format['format_bold'])
            server_sheet.set_column(0, 0, 20)
            server_sheet.set_tab_color(color="green")
            total_sheet.write_row(row=idx + 1, col=0, data=(current_server.upper(), "Upgade is not needed", patches_str[1],patches_str[2]), cell_format=format['format_green'])
            total_sheet.write_url(row=idx + 1, col=0,url="internal:'{sheet_name}'!A1".format(sheet_name=current_server.upper()), cell_format=format['format_green_url'], string=current_server.upper())
        total_sheet.conditional_format(first_row=idx + 1, first_col=2, last_row=idx + 1, last_col=3, options={'type': 'text', 'criteria': 'containing', 'value': 'yes', 'format': format['format_red']})
        total_sheet.conditional_format(first_row=idx + 1, first_col=2, last_row=idx + 1, last_col=3, options={'type': 'text', 'criteria': 'containing', 'value': 'no', 'format': format['format_green']})
        col_width=(15,34,14,14)
        for i in range(0,4):
            total_sheet.set_column(i,i,col_width[i])
    xlsx_file.close()

def send_email_with_xlsx_to_customer(group_of_servers):
    names=group_of_servers.split(',')
    final_names=[n.split(' ')[0] for n in names]
    if len(final_names)>1:
        final_names=', '.join(final_names[:-1]) + " and " + final_names[-1]
    else:
        final_names=final_names[0]
    print(final_names)
    return 0
    e_mails=db_cur.execute("SELECT CONTACT_EMAILS FROM SERVER_OWNERS_EMAILS WHERE SERVICE_OWNERS=:group_of_servers", {'group_of_servers' : group_of_servers}).fetchone()
    mail_body="<html><head></head><body>\
    <p><font color=f02a00>This is a test message, not real, please, ignore. I am only need a real e-mails for perform several tests with new script</font></p>\
    <p>Hello {names},</p>\
    \
    <p>This is e-mail regarding to list of updates for future Linux patching cycle. \
    In attached Excel-file you can find servers with available patches.</p>\
    \
    <p><b><u>Please, note:</b></u><br>\
    1) Patches list have been gather recently. During month new patches may be released and we will install all of them<br>\
    2) We can exclude several patches which can affect to application stability<br>\
    3) All servers can be rebooted if new kernel or packages which require reboot will be released during month<br>\
    4) Patches which can affect a application stability can be exluded from patching cycle. This is mean that server can still vulnerable to several threat<br>\
    5) Server will not be patched if no patches in attached xlsx-file.</p>\
    <p>Please, reply to this e-mail if you have any concerns\questions. Also reply to this e-mail if you want to change patching contacts for your servers./<p>\
    Have a nice day!\
    {sign}</body></html>".format(names=final_names, sign=settings["sign"])
    msg = MIMEMultipart('related')
    msg_a = MIMEMultipart('alternative')
    msg.attach(msg_a)
    txt=''
    part1 = MIMEText(txt, 'plain')
    part2 = MIMEText(mail_body, 'html')
    msg_a.attach(part1)
    msg_a.attach(part2)
    part3 = MIMEBase('application', "octet-stream")
    part3.set_payload(open('/tmp/patching_list.xlsx', "rb").read())
    encoders.encode_base64(part3)
    part3.add_header('Content-Disposition', 'attachment', filename='patching_list.xlsx')
    msg_a.attach(part3)
    logo = open('../images/VRFwMw2.png', 'rb')
    part4 = MIMEImage(logo.read())
    logo.close()
    part4.add_header('Content-ID', '<logo>')
    msg.attach(part4)
    msg['Subject'] = "[TEST MESSAGE, PLEASE IGNORE] Upcomming Linux patching -- {month}, list of updates".format(month=today.strftime("%B"))
    msg['From'] = settings['email_from']
    msg['To'] = ','.join(e_mails)
    msg['Cc'] = settings['e_mail_cc']
    try:
        s = smtplib.SMTP(settings['smtp_server'])
        s.sendmail(msg['From'], msg['To'].split(',') + settings['e_mail_cc'].split(','), msg.as_string())
        s.quit()
        print('e_mail was sent correctly')
    except Exception as e:
        termcolor.cprint('Error occured during sendig e-mail. Exception: ', color='red', on_color='on_white')
        print(e)
        return None

def main():
    '''main function'''
    #get the list of files in directory
    servers_list=os.listdir("./")
    servers_list.remove('total.csv')
    #get the unique so with affected servers as dict, see example in function description
    uniq_so_group_with_servers=return_server_groups(servers_list)
    #generate xlsx-file for each new group
    for current_group_of_project, current_uniq_so_group_servers in uniq_so_group_with_servers.items():
        prepare_xlsx_file(current_uniq_so_group_servers)
        send_email_with_xlsx_to_customer(current_group_of_project)


db_cur=sqlite3.connect('./patching_dev.db').cursor()
settings = get_settings()
today=datetime.datetime.now()
os.chdir(os.path.dirname(os.path.realpath(__file__)) + today.strftime("%b_%Y") + '_separate_csv_with_patching_list/')
csv_file=open("./total.csv", 'r')
csv_reader=csv.reader(csv_file, delimiter=';')

main()
