#!/usr/bin/python3
import sqlite3
import datetime
import random
import csv
import smtplib
import glob
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import sys
import os
from distutils.sysconfig import get_python_lib
from operator import itemgetter
import logging

os.chdir(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(get_python_lib())

logging.basicConfig(filename="/var/log/patching/patching_auto_email_before_4_days.log", filemode="a", format="%(asctime)s %(message)s", datefmt="%d/%m/%Y %H:%M:%S", level=logging.INFO)
logging.info("Starting the script...")

def get_settings():
    '''Function for get settings from txt-file and return dictionary'''
    settings={}
    exec(open("./settings_email.txt").read(), None, settings)
    return settings

def extract_needed_servers():
    '''function for read csv files and extract servers which should be patched between now+13 min. and now+28 min.'''
    logging.info("Searching needed servers...")
    servers_for_sending_email = {}
    csv_files=glob.glob('./*before_4_days*.csv')
    logging.info("Working with these csv-files: {csv}".format(csv=str(csv_files)))
    for csv_file_for_open in csv_files:
        csv_file = open(csv_file_for_open)
        min_start_time = datetime.datetime.now() + datetime.timedelta(minutes=58, hours=15, days=3)
        # max_start_time = datetime.datetime.now() + datetime.timedelta(minutes=30)
        max_start_time = datetime.datetime.now() + datetime.timedelta(hours=16, days=4)
        patching_schedule_csv = csv.reader(csv_file, delimiter=';')
        for row in patching_schedule_csv:
            patching_start_time = datetime.datetime.strptime(row[1], '%d.%m.%Y %H:%M')
            if patching_start_time > min_start_time and patching_start_time < max_start_time:
                servers_for_sending_email[row[0]] = row[1]
        csv_file.close()
    if servers_for_sending_email:
        logging.info(
            "Server(s) which will be patches in 4 days: {servers}".format(servers=" ".join(servers_for_sending_email)))
        return servers_for_sending_email
    else:
        return None


def extract_emails_and_so(servers):
    '''return server name, SO, e-mails, project name'''
    logging.info("Connecting to sqlite3 database")
    patching_db=sqlite3.connect('./patching.db')
    cursor_patching_db = patching_db.cursor()
    servers_contact = []
    for current_server in servers.keys():
        data_from_sqlite = cursor_patching_db.execute(
            'SELECT SERVER_NAME,SERVICE_OWNERS,CONTACT_EMAILS,PROJECT_NAME FROM SERVERS INNER JOIN SERVER_OWNERS_EMAILS ON SERVERS.PROJECT = SERVER_OWNERS_EMAILS.PROJECT_NAME WHERE SERVER_NAME=:current_server',
            {'current_server': current_server}).fetchone()
        if data_from_sqlite:
            servers_contact.append(data_from_sqlite + tuple([servers[current_server]]))
    return servers_contact


def email_sending(server_so_email):
    '''Example of function's argument
    server_so_email = [('cent_os7', 'User1 User1,User2 User2', 'user1@users.com,users2@users.com',
                        'Nagios main nodes', '04.01.2018 20:00')]'''
    logging.info("Trying to send e-mail to customer...")
    e_mails=[]
    server_so_email.sort(key=itemgetter(1))
    cells="<tr><td><b>Server name</b></td><td><b>Patching date</b></td><td><b>Patching contacts</b></td><td><b>Server group</b></td></tr>"
    for current_server in server_so_email:
        cells+="<tr><td>{server_name}</td><td>{patching_date}</td><td>{patching_contacts}</td><td>{project_name}</td></tr>".format(server_name=current_server[0].upper(), patching_date=current_server[4],
                                                                                                                              patching_contacts=current_server[2], project_name=current_server[3])
        logging.info("E-mail will be sent for this server: {serv}".format(serv=str(current_server[0])))
        logging.info("And e-mail(s): {mail}".format(mail=current_server[2]))
        for current_e_mail in current_server[2].split(","):
            if current_e_mail not in e_mails:
                e_mails.append(current_e_mail)
    if cells:
        bye=('Best regards,', 'Kind regards,')[random.randint(0,1)]
        message = """<html><head></head><body>Dear Customer,<br><br>Please, be informed regarding to upcoming patching. Additional information:<br> <table border="1">{servers}</table><br><br>{bye}{sign}</body></html>""".format(servers=cells, bye=bye, sign=settings['sign'])
    subject = 'RFC {rfc_number}: monthly Linux-patching'.format(rfc_number=rfc_number)
    msg = MIMEMultipart('related')
    msg_a = MIMEMultipart('alternative')
    msg.attach(msg_a)
    txt=''
    part1 = MIMEText(txt, 'plain')
    part2 = MIMEText(message, 'html')
    logo=open('./images/VRFwMw2.png', 'rb')
    part3 = MIMEImage(logo.read())
    logo.close()
    part3.add_header('Content-ID', '<logo>')
    msg_a.attach(part1)
    msg_a.attach(part2)
    msg.attach(part3)
    msg['Subject'] = subject
    msg['From'] = settings['email_from']
    msg['To'] = ",".join(e_mails)
    msg['Cc'] = settings['e_mail_cc_before_3_days']
    try:
        logging.info("Connecting to {smtp} smtp-server...".format(smtp=settings["smtp_server"]))
        s = smtplib.SMTP(settings['smtp_server'])
        s.sendmail(msg['From'], e_mails + settings['e_mail_cc_before_4_days'].split(','), msg.as_string())
        s.quit()
        logging.info("E-mail has been sent successfully!")
    except Exception as e:
        logging.critical("Error during e-mail sending. Exception: {exception}".format(exception=str(e)))


settings=get_settings()
rfc_number=open('rfc_number.txt', 'r').read().rstrip()

servers_whcih_will_be_patchesd_in_4_days=extract_needed_servers()

if servers_whcih_will_be_patchesd_in_4_days:
    server_so_email_date = extract_emails_and_so(servers_whcih_will_be_patchesd_in_4_days)
    email_sending(server_so_email_date)
else:
    logging.info("There are no servers which will be patched in 4 days...")
