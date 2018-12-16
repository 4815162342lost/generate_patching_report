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
from auto_mm import get_patching_start_date
import csv
import datetime
import configparser
import logging
import pytz

log_file=logging.basicConfig(filename=os.path.dirname(os.path.realpath(__file__))+ '/send_separate_emails_error.log', level=logging.INFO,  datefmt="%d/%m%Y %H:%M:%S", format="%(asctime)s %(message)s")

def get_settings():
    '''parse the config file'''
    parse_conf=configparser.ConfigParser()
    parse_conf.read("./settings.cfg")
    return parse_conf['auto_e_mail_separate_to_so_with_pacthing_list']


def return_server_groups(server_list):
    '''return the dict which contain service owner e-mails and servers'''
    server_groups={}
    for current_server in server_list:
        so_email=db_cur.execute("SELECT SERVER_OWNERS_EMAILS.CONTACT_EMAILS FROM SERVER_OWNERS_EMAILS\
                          INNER JOIN SERVERS ON SERVER_OWNERS_EMAILS.PROJECT_NAME=SERVERS.PROJECT\
                          WHERE SERVERS.SERVER_NAME=:server_name COLLATE NOCASE", {'server_name' : current_server}).fetchone()
        #if new key -- create them, if old -- only append new value
        try:
            if so_email[0] not in server_groups:
                server_groups[so_email[0]]=[current_server]
            else:
                server_groups[so_email[0]].append(current_server)
        except TypeError:
            termcolor.cprint("Error: {server} server is not found on local database, ignoring...".format(server=current_server), color="white", on_color="on_red" )
            logging.warning('Error: {server} server is not found on local database, ignoring...'.format(server=current_server))
    #example: {'Faith.Connor@my_retard.com,Zoey.Coatcher@my_retard.com': ['cent_os', 'secret_server'], 'Lous.Coatcher@myretard.com,Our_team@my_retard.com': ['server22']}
    return server_groups


def prepare_xlsx_file(servers):
    '''Function for generate xlsx-files and write them to /tmp/ directory, servers -- list of servers'''
    #create xsls-file, total_sheet and get formats
    servers_which_not_find_in_total_csv_file=0
    termcolor.cprint("Working with {servers} servers(s)...".format(servers=servers), color="white", on_color="on_green")
    xlsx_file=xlsxwriter.Workbook('/tmp/patching_list.xlsx')
    format = create_formats(xlsx_file)
    total_sheet=xlsx_file.add_worksheet("Total")
    total_sheet.set_tab_color(color="yellow")
    total_sheet.write_row(row=0, col=0,data=("Server name", "Conclusion", "Kernel upgrade", "Reboot required"), cell_format=format['format_bold'])
    table="<table border='1'><tr><td>Server name</td><td>Patching start time</td><td>Patching end time</td><td>Patching time zone</td></tr>"
    for idx, current_server in enumerate(servers):
        # change the position in file to beginning
        csv_file.seek(0)
        need_proceed=False
        #crete sheet with server name and open txt-file with server
        server_sheet=xlsx_file.add_worksheet(current_server.upper())
        server_file_csv=csv.reader(open(current_server.lower(), 'r'), delimiter=';')
        #extract the line which related with current server from total.csv file, save this line to patches_str variable
        for row in csv_reader:
            if row[0]==current_server:
                patches_str=row;
                need_proceed=True
                break
        #if server is not found in total.csv file
        if not need_proceed:
            termcolor.cprint('Can not find the {server} server in total.csv file. Skipping...'.format(server=current_server), color="white", on_color="on_red")
            logging.warning('Can not find the {server} server in total.csv file. Skipping...'.format(server=current_server))
            servers_which_not_find_in_total_csv_file+=1
            continue
        #if server should be patched
        if int(patches_str[3])!=0:
            patching_code, start_time, patching_duration, time_zone =db_cur.execute("SELECT WINDOW_CODE, START_TIME, DURATION_TIME, TIMEZONE FROM SERVERS WHERE SERVER_NAME=:server_name COLLATE NOCASE", {'server_name': current_server}).fetchone()
            start_date = get_patching_start_date(today, patching_code, db_cur)
            start_date=datetime.datetime(year=start_date.year, month=start_date.month, day=start_date.day, hour=int(start_time[0:2]), minute=int(start_time[3:5]))
            end_datetime_datetime=start_date + datetime.timedelta(hours=int(patching_duration[0:2]), minutes=int(patching_duration[3:5]))
            table += "<tr><td>{server_name}</td><td>{start}</td><td>{end}</td><td>{time_zone}</td></tr>\n".format(server_name=current_server.upper(), \
                    start=start_date.strftime("%d/%m/%Y %H:%M"), time_zone=pytz.timezone(time_zone).tzname(start_date), end=end_datetime_datetime.strftime("%d/%m/%Y %H:%M"))
            suse=False
            server_sheet.write(0,0, "{count} packages will be updated".format(count=patches_str[3]), format['format_bold'])
            server_sheet.write_row(1, 0, next(server_file_csv)[0:3], cell_format=format['format_bold'])
            for idx1, current_patch in enumerate(server_file_csv):
                # my script can not extract installed and availble version for Suse Linux. Need avoid 'none' entries in 'current version' and 'available version'
                #cxv example for suse Linux, we see 'none'
                #Package name;Current version;Available version
                #Security update for Mozilla Firefox and NSS;none;none
                #Security update for java-1_8_0-openjdk;none;none
                if idx1==0 and current_patch[1]=='none':
                    suse=True
                    server_sheet.write(1, 0, 'Update description', format['format_bold'])
                    #remove 'current version' and 'available version from Excel file'
                    for i in range(1,3):
                        server_sheet.write(1, i, ' ')
                #if not suse write patch name, current and available versions, else -- write only update dscription
                if not suse:
                    server_sheet.write_row(idx1 + 2, 0, current_patch, cell_format=format['format_border'])
                else:
                    server_sheet.write(idx1 + 2, 0, current_patch[0], format['format_border'])
            #set width for column
            for current_width in range(4, 7):
                server_sheet.set_column(current_width - 4, current_width - 4, width=int(patches_str[current_width]))
            server_sheet.set_tab_color(color="red")
            #write to tatoal sheet
            total_sheet.write_row(row=idx+1, col=0,data=(current_server.upper(), "{count} packages need to update".format(count=patches_str[3]), patches_str[1], patches_str[2]), cell_format=format['format_red'])
            total_sheet.write_url(row=idx + 1, col=0, url="internal:'{sheet_name}'!A1".format(sheet_name=current_server.upper()),cell_format=format['format_red_url'], string=current_server.upper())
        #if not patches
        else:
            #add server to html_tabe
            table+="<tr><td>{server_name}</td><td>No updates available</td><td> </td><td> </td></tr>".format(server_name=current_server.upper())
            server_sheet.write(0, 0, "Upgrade is not needed", format['format_bold'])
            server_sheet.set_column(0, 0, 20)
            server_sheet.set_tab_color(color="green")
            total_sheet.write_row(row=idx + 1, col=0, data=(current_server.upper(), "Upgade is not needed", patches_str[1],patches_str[2]), cell_format=format['format_green'])
            total_sheet.write_url(row=idx + 1, col=0,url="internal:'{sheet_name}'!A1".format(sheet_name=current_server.upper()), cell_format=format['format_green_url'], string=current_server.upper())
        #set the colors for 'yes\no' cells. Yes, i know, ugly and hard, but funny and works
        total_sheet.conditional_format(first_row=idx + 1, first_col=2, last_row=idx + 1, last_col=3, options={'type': 'text', 'criteria': 'containing', 'value': 'yes', 'format': format['format_red']})
        total_sheet.conditional_format(first_row=idx + 1, first_col=2, last_row=idx + 1, last_col=3, options={'type': 'text', 'criteria': 'containing', 'value': 'no', 'format': format['format_green']})
        col_width=(20,34,14,14)
        for i in range(0,4):
            total_sheet.set_column(i,i,col_width[i])
    xlsx_file.close()
    table+="</table>"
    #if all servers from function input is not exists in total.csv file -- not need to send xlsx-file to customer
    if servers_which_not_find_in_total_csv_file!=len(servers):
        return table
    else:
        return 1


def send_email_with_xlsx_to_customer(group_of_e_mails, table):
    '''group_of_e_mails -- e-mails of service owners (only emails)'''
    names = db_cur.execute("SELECT SERVICE_OWNERS FROM SERVER_OWNERS_EMAILS WHERE CONTACT_EMAILS=:e_mails LIMIT 1",{'e_mails': group_of_e_mails}).fetchone()[0].split(",")
    final_names=[n.split(' ')[0] for n in names]
    if len(final_names)>1:
        final_names=', '.join(final_names[:-1]) + " and " + final_names[-1]
    else:
        final_names=final_names[0]
    mail_body="<html><head><meta charset='UTF-8'></head><body>\
    <p>Dear {names},</p>\
    Please see below the list of the Linux servers under your responsibility, with the exact patching schedule for each of them.\
    <br>The list of updates is attached to this email.\
    <p>{table}</p>\
    <br>In case any clarifications or schedule corrections are required, please <b>REPLY ALL.</b>\
    <br>If you start experiencing any issues after the patching date, please create an incident for <b>{itsm_group}</b> group.\
    {sign}</body></html>".format(names=final_names, sign=settings["sign"], table=table, itsm_group=settings['itsm_group'])
    msg = MIMEMultipart('related')
    msg_a = MIMEMultipart('alternative')
    msg.attach(msg_a)
    part2 = MIMEText(mail_body, 'html')
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
    msg['Subject'] = "Upcoming Linux patching -- {month} | RFC {rfc_number}".format(month=today.strftime("%B"), rfc_number=rfc_number)
    msg['From'] = settings['email_from']
    msg['To'] = group_of_e_mails
    msg['Cc'] = settings['e_mail_cc']
    try:
        s = smtplib.SMTP(settings['smtp_server'])
        s.sendmail(msg['From'], group_of_e_mails.split(",") + settings['e_mail_cc'].split(','), msg.as_string())
        s.quit()
        termcolor.cprint('E_mail was sent correctly to {e_mails}!'.format(e_mails=msg['To']), color="white", on_color="on_green")
    except:
        termcolor.cprint("Can not send the e-mail to {e_mails} first time, trying again...".format(e_mails=msg['To']), color="red", on_color="on_white")
        try:
            s = smtplib.SMTP(settings['smtp_server'])
            s.sendmail(msg['From'], group_of_e_mails.split(",") + settings['e_mail_cc'].split(','), msg.as_string())
            s.quit()
            termcolor.cprint('E_mail was sent correctly in this time!', color="white", on_color="on_green")
        except Exception as e:
            termcolor.cprint('Error occured during sendig e-mail again... Skipping this message.  Exception: {ex} '.format(ex=str(e)), color='red', on_color='on_white')
            logging.warning("Can not send the e-mail to {e_mails}".format(e_mails=msg['To']))
    input("Please, enter any symbol to proceed...")

def main():
    '''main function'''
    #get the list of files in directory
    servers_list=os.listdir("./")
    servers_list.remove('total.csv')
    #get the unique so with affected servers as dict, see example in function description
    uniq_so_e_mails_group_with_servers=return_server_groups(servers_list)
    #generate xlsx-file for each new group
    for e_mails, servers in uniq_so_e_mails_group_with_servers.items():
        #print if need send e-mail with xlsx-file
        table=prepare_xlsx_file(servers)
        if table!=1:
            send_email_with_xlsx_to_customer(e_mails, table)
        else:
            termcolor.cprint("E-mail for these {current_uniq_so_group_servers} server(s) will not be send to customer due to errors above...".format(current_uniq_so_group_servers=servers), color="white", on_color="on_red")
            logging.warning("Error: e-mail for these {current_uniq_so_group_servers} server(s) will not be send to customer...".format(current_uniq_so_group_servers=servers))

db_cur=sqlite3.connect('./patching_dev.db').cursor()
settings = get_settings()
today=datetime.datetime.now()

rfc_number=open('./rfc_number.txt').read().rstrip()

termcolor.cprint("                             /T /I\n\
                              / |/ | .-~/\n\
                          T\ Y  I  |/  /  _\n\
         /T               | \I  |  I  Y.-~/\n\
        I l   /I       T\ |  |  l  |  T  /\n\
     T\ |  \ Y l  /T   | \I  l   \ `  l Y\n\
 __  | \l   \l  \I l __l  l   \   `  _. |\n\
 \ ~-l  `\   `\  \  \\ ~\  \   `. .-~   |\n\
  \   ~-. \"-.  `  \  ^._ ^. \"-.  /  \   |\n\
.--~-._  ~-  `  _  ~-_.-\"-.\" ._ /._ .\" ./\n\
 >--.  ~-.   ._  ~>-\"    \"\\   7   7   ]\n\
^.___~\"--._    ~-{  .-~ .  `\ Y . /    |\n\
 <__ ~\"-.  ~       /_/   \   \I  Y   : |\n\
   ^-.__           ~(_/   \   >._:   | l______\n\
       ^--.,___.-~\"  /_/   !  `-.~\"--l_ /     ~\"-.\n\
              (_/ .  ~(   /'     \"~\"--,Y   -=b-. _)\n\
               (_/ .  \  :           / l      c\"~o \ \n\
                \ /    `.    .     .^   \_.-~\"~--.  )\n\
                 (_/ .   `  /     /       !       )/\n\
                  / / _.   '.   .':      /        '\n\
                  ~(_/ .   /    _  `  .-<_\n\
                    /_/ . ' .-~\" `.  / \  \          ,z=.\n\
                    ~( /   '  :   | K   \"-.~-.______//\n\
                      \"-,.    l   I/ \_    __{--->._(==.\n\
                       //(     \  <    ~\"~\"     //\n\
                      /' /\     \  \     ,v=.  ((\n\
                    .^. / /\     \"  }__ //===-  `\n\
                   / / ' '  \"-.,__ {---(==-       -Row\n\
                 .^ '       :  T  ~\"   ll\n\
                / .  .  . : | :!        \\\n\
               (_/  /   | | j-\"          ~^\n\
                 ~-<_(_.^-~\"", color="magenta", on_color="on_white")
try:
    os.chdir(os.path.dirname(os.path.realpath(__file__)) + '/' + today.strftime("%b_%Y") + '_separate_csv_with_patching_list/')
except FileNotFoundError:
    termcolor.cprint('./' + today.strftime("%b_%Y") + '_separate_csv_with_patching_list/ directory is not found, can not proceed, exiting...', color="white", on_color="on_red")
    exit()
try:
    csv_file=open("./total.csv", 'r')
except FileNotFoundError:
    termcolor.cprint("Common total.csv file is not found. Exiting, can not proceed...", color="white", on_color="on_red")
    exit()
csv_reader=csv.reader(csv_file, delimiter=';')

main()
