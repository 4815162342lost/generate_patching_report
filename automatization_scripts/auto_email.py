#!/usr/bin/python3
import sqlite3
import datetime
import random
import csv
import itertools
import smtplib
import glob
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import sys
import os
from distutils.sysconfig import get_python_lib
import logging
import configparser

logging.basicConfig(filename="/var/log/patching/patching_auto_email.log", filemode="a", format="%(asctime)s %(message)s", datefmt="%d/%m/%Y %H:%M:%S", level=logging.INFO)
logging.info("==================================================================")
logging.info("Starting the script...")

os.chdir(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(get_python_lib())


def get_settings():
    '''parse the config file'''
    parse_conf=configparser.ConfigParser()
    parse_conf.read("./settings.cfg")
    return parse_conf['auto_e_mail_notifications']


def extract_needed_servers():
    '''function for read csv files and extract servers which should be patched between now+13 min. and now+28 min.'''
    logging.info("Searching needed servers from csv-files...")
    servers_for_sending_email = {}
    csv_files=glob.glob('./*linux_MM*.csv')
    logging.info("Working with these csv-files: {csv}".format(csv=str(csv_files)))
    for csv_file_for_open in csv_files:
        csv_file = open(csv_file_for_open)
        min_start_time = datetime.datetime.now() + datetime.timedelta(minutes=13)
        max_start_time = datetime.datetime.now() + datetime.timedelta(minutes=28)
        patching_schedule_csv = csv.reader(csv_file, delimiter=';')
        for row in itertools.islice(patching_schedule_csv, 1, None):
            patching_start_time = datetime.datetime.strptime(row[1], '%d.%m.%Y %H:%M')
            if patching_start_time > min_start_time and patching_start_time < max_start_time:
                servers_for_sending_email[row[5]] = row[1]
        csv_file.close()
    if servers_for_sending_email:
        logging.info("Server(s) which will be patches soon: {servers}".format(servers=" ".join(servers_for_sending_email)))
        return servers_for_sending_email
    else:
        return None


def extract_emails_and_so(servers):
    '''return server name, SO, e-mails, project name'''
    logging.info("Connecting to sqlite3 database...")
    connect_patching_db = sqlite3.connect('./patching.db')
    cursor_patching_db=connect_patching_db.cursor()
    servers_contact = []
    for current_server in servers.keys():
        data_from_sqlite = cursor_patching_db.execute(
            'SELECT SERVER_NAME,SERVICE_OWNERS,CONTACT_EMAILS,PROJECT_NAME FROM SERVERS INNER JOIN SERVER_OWNERS_EMAILS ON SERVERS.PROJECT = SERVER_OWNERS_EMAILS.PROJECT_NAME WHERE SERVER_NAME=:current_server',
            {'current_server': current_server}).fetchone()
        if data_from_sqlite:
            servers_contact.append(data_from_sqlite + tuple([servers[current_server]]))
    connect_patching_db.close()
    return servers_contact


def prepare_email(server_for_sending_emails):
    '''Example of function's argument
    server_so_email = [('cent_os7', 'User1 User1,User2 User2', 'user1@users.com,users2@users.com',
                        'Nagios main nodes', '04.01.2018 20:00')]'''
    uniq_so_and_emails_set = []
    for current_server in server_for_sending_emails:
        uniq_so_and_emails_set.append((current_server[1], current_server[2], current_server[3], current_server[4]))
    uniq_so_and_emails_set = set(uniq_so_and_emails_set)
    logging.info("Starting grouping servers...")
    common_servers = []
    for current_server_in_uniq in uniq_so_and_emails_set:
        counter = 0
        for current_server in server_for_sending_emails:
            for i in range(1, 5):
                if current_server[i] == current_server_in_uniq[i - 1]:
                    counter += 1
            #if all attributes are same
            if counter == 4:
                common_servers.append(current_server[0].upper())
                params = current_server[1:]
            counter = 0
        email_sending(common_servers, params)
        common_servers.clear()

def email_sending(servers_for_sending_emails, params):
    '''Function for send e-mail'''
    logging.info("Trying to send e-mail to customer...")
    logging.info("Servers whcih will be in current e-mail: {servers}".format(servers=" ".join(servers_for_sending_emails)))
    logging.info("Customer names: {names}, e-mails: {emails}, project name {project_name}, date: {date}".format(names=params[0], emails=params[1], project_name=params[2], date=params[3]))
    so_str = ''
    services_owners = params[0].split(',')
    if len(services_owners) == 1:
        so_str = services_owners[0].split(' ')[0]
    elif len(services_owners) > 1:
        for i in services_owners[:-1]:
            so_str += (i.split(' ')[0]) + ', '
        so_str += str(' and ' + services_owners[-1].split(' ')[0])
        so_str = so_str.replace(',  and', ' and')

    servers_str=''
    if len(servers_for_sending_emails)==1:
        servers_str='of <b><font color=bc6c03>%s</font></b> server will be started at <b><u>%s CET</u></b>.'% (servers_for_sending_emails[0],params[3].split(' ')[1])
    elif len(servers_for_sending_emails)>1:
        servers_str='of following servers will be started at <b><u>{date} CET:<br></u></b><b><font color=bc6c03>{servers}</font></b>'\
            .format(date=params[3].split(' ')[1], servers='<br>'.join(servers_for_sending_emails))
    bye=('Best regards,', 'Kind regards,')[random.randint(0,1)]
    message = """<html><head></head><body>Dear {SO},<br><br>Please be informed that patching {servers}<br><br>{bye}{sign}</body></html>""".format(SO=so_str, date=params[3], servers=servers_str, bye=bye, sign=settings["sign"])
    subject = 'RFC {rfc_number}: monthly Linux-patching ('.format(rfc_number=rfc_number) + params[2] + ')'
    e_mails= params[1]
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
    msg['From'] = settings["email_from"]
    msg['To'] = e_mails
    msg['Cc'] = settings["e_mails_cc"]
    try:
        logging.info("Connecting to {smtp} smtp-server...".format(smtp=settings["smtp_server"]))
        s = smtplib.SMTP(settings["smtp_server"])
        s.sendmail(msg['From'], e_mails.split(',') + settings["e_mails_cc"].split(','), msg.as_string())
        s.quit()
        logging.info("E-mail has been sent successfully!")
    except Exception as e:
        logging.critical("Error during e-mail sending. Exception: {exception}".format(exception=str(e)))


settings=get_settings()
rfc_number=open('rfc_number.txt', 'r').read().rstrip()
servers_which_will_be_patched_soon=extract_needed_servers()
if servers_which_will_be_patched_soon:
    server_so_email_date = extract_emails_and_so(servers_which_will_be_patched_soon)
    prepare_email(server_so_email_date)
else:
    logging.info("There are no servers which will be patched soon")
logging.info("Exiting. Bye-bye...")
