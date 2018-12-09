#!/usr/bin/python3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.encoders import encode_base64
import base64
import pytz
import smtplib
import datetime
import icalendar
import sqlite3
import csv
import itertools
import glob
import termcolor
import configparser
import os
import sys
from distutils.sysconfig import get_python_lib
sys.path.append(get_python_lib())
sys.path.append('/usr/local/lib/python3.5/site-packages')
import openpyxl
import dateutil
import hashlib
import random
import argparse

sys.path.append(get_python_lib())
os.chdir(os.path.dirname(os.path.realpath(__file__)))

def parse_args():
    args=argparse.ArgumentParser()
    args.add_argument("-m", '--md5', type=str, required=False, help="notification hash which must be cancelled")
    return args.parse_args()




def get_settings():
    '''return settings from settings.cfg file'''
    parse_conf=configparser.ConfigParser()
    parse_conf.read("./settings.cfg")
    return parse_conf['auto_outlook_notifocations']


def return_information_from_xlsx_file(server_name):
    '''find the row with server in Excel file and return it'''
    temp_var=[]; min_value=1
    for max_value in (100,200,300,400,500,600,700,800,900,1000):
        for line in sheet_with_schedule['C{min_s}:P{max_s}'.format(max_s=max_value,min_s=min_value)]:
            #create list from rows from excel file
            for row in line:
                temp_var.append(row.value)
            #if first column in current row(list) is empty -- values in Excel file empty, necessary server is not found
            if temp_var[0]==None:
                return []
            #if we found our server in Excel file -- return list with server
            if temp_var[0].lower().rstrip()==server_name:
                return temp_var
            temp_var.clear()
        min_value=max_value+1


def extract_uniq_date_and_time_groups(csv_files):
    '''create new dict, key -- unique datetime, valuses -- server_names'''
    uniq_datetime_dict_with_servers={}
    for current_csv in csv_files:
        csv_reader=csv.reader(open(current_csv, 'r'), delimiter=';')
        for current_csv_line in itertools.islice(csv_reader, 1, None):
            if current_csv_line[1] in uniq_datetime_dict_with_servers:
                uniq_datetime_dict_with_servers[current_csv_line[1]].append(current_csv_line[5])
            else:
                uniq_datetime_dict_with_servers[current_csv_line[1]]=[current_csv_line[5]]
    #example: {'25.12.2018 16:00': ['cent_os', 'cent_os_2']}
    return uniq_datetime_dict_with_servers


def return_utc(date):
    '''Function for convert local timezone to UTC. Outlook can not work properly with local time (or i am a retard)'''
    utc_zone = dateutil.tz.gettz('UTC')
    local_zone = dateutil.tz.gettz('Europe/Paris')
    date = date.replace(tzinfo=local_zone)
    utc_time = date.astimezone(utc_zone)
    return str(utc_time.strftime("%d-%m-%Y %H:%M"))


def prepare_email(patching_date, extracted_data_from_excel, project_name, need_to_add_dba_team):
    '''Function for prepare e-mail's body'''
    # ['server_1', 'Critical', 'CentOS 7', 'Production', 'US-DC', 'Faith Connor/Zoey Peaches', 'File-server', None,
    #  'PATCHING_CODE', datetime.datetime(2018, 11, 27, 0, 0), '16:00 - 20:00 CET', 'mysql-server_1',
    #  'These two servers are members of a cluster and should not be rebooted at the same time.
    #  'e_mail_1@my_org.com; e_mail_2@my_org.com]

    attendees=settings[cursor_patching_db.execute("SELECT ATTENDEE_GROUP FROM SERVER_OWNERS_EMAILS WHERE PROJECT_NAME=:project_name", {'project_name' : project_name}).fetchone()[0]]
    if need_to_add_dba_team:
        attendees+="," + settings['dba_team_e_mail']
    patching_start_date=datetime.datetime.strptime(patching_date, '%d.%m.%Y %H:%M')
    possible_colors = ('#f6cec2 ', '#cef6c2 ', '#c2f5f6 ', '#cecbf2 ', '#f5f3ad ')
    event_uid=str(hashlib.md5((str(datetime.datetime.utcnow()) + str(random.randint(10000,99999))).encode("utf-8")).hexdigest())
    table_with_servers='<table><tr bgcolor="#e1f65d"><th text-align="centre">Server</th><th>OS</th><th>Environment</th><th>Patching date</th><th>Patching time</th><th>Patching contacts</th>\
    <th>Additional mm</th><th>Special instructions</th></tr>'
    for idx, current_data_from_excel in enumerate(extracted_data_from_excel):
        try:
            table_with_servers+='<tr bgcolor={color}><th>{server_name}</th><th>{os_type}</th><th>{env}</th><th>{start_date}</th><th>{start_time}</th><th>{contacts}\
            </th><th>{additional_mm}</th><th>{special_instructions}</th></tr>'.\
                format(server_name=current_data_from_excel[1].upper(), os_type=current_data_from_excel[0][2], env=current_data_from_excel[0][3],\
                start_date=current_data_from_excel[0][9].strftime("%d %m %Y"), start_time=current_data_from_excel[0][10], contacts=current_data_from_excel[0][13],
                       color=possible_colors[idx%5], additional_mm=current_data_from_excel[0][11], special_instructions=current_data_from_excel[0][12])
        except (AttributeError,IndexError):
            print("Error with {server} server".format(server=current_data_from_excel[1].upper()))
    table_with_servers+='</table>'

    body='<html><head><meta charset="UTF-8"><style>table, th, td {{border: 1px solid black;border-collapse: collapse;}}th, td {{padding: 5px;text-align: center;}}</style></head><body>\
    <br><b><font size=3>HASH: {hash}</font></b><br><br><b>Linux administrators</b>, please, perform this patching at <b>{patching_time} CET:</b>\
    <br>{table_with_servers}</body></html>'.format(patching_time=patching_start_date, table_with_servers=table_with_servers, hash=event_uid)
    send_notify_email(body, patching_start_date, project_name, attendees, event_uid)


def check_need_database_or_not(server_name):
    additioanl_cis = cursor_patching_db.execute("SELECT ADDITIONAL_CIS FROM ADDITIONAL_MONITORS WHERE SERVER_NAME=:server COLLATE NOCASE", {'server': server_name}).fetchall()
    for current_additional_cis in additioanl_cis:
        if current_additional_cis[0].lower().find("oracle") != -1 or current_additional_cis[0].lower().find("mysql") != -1:
            return True
    return False


def return_uniq_groups(servers):
    need_databas_team=False
    uniq_project={}
    for current_server in servers:
        project_name=cursor_patching_db.execute("SELECT PROJECT FROM SERVERS WHERE SERVER_NAME=:server COLLATE NOCASE", {'server': current_server}).fetchone()[0]
        if project_name not in uniq_project:
            uniq_project[project_name]=[current_server]
            if check_need_database_or_not(current_server):
                uniq_project[project_name].append("dba_needed")
                need_databas_team=True
        else:
            uniq_project[project_name].append(current_server)
            if not need_databas_team:
                if check_need_database_or_not(current_server):
                    uniq_project[project_name].append("dba_needed")
                    need_databas_team=True
    # example: {'UNIQ_GROUP_1': ['server_1'], 'UNIQ_GROUP_2': ['server_2', 'server_3']}
    return uniq_project


def send_notify_email(body, start_time, title, attendees, event_uid):
    subject = 'Linux Monthly Patching {month} | RFC {rfc_number} {project}'.format(
        month=datetime.datetime.now().strftime("%B %Y"), rfc_number=rfc_number, project=title)
    start_time_utc=return_utc(start_time)
    cal = icalendar.Calendar()
    cal.add('prodid', '-//My calendar application//example.com//')
    cal.add('version', '2.0')
    cal.add('method', 'REQUEST')
    event = icalendar.Event()
    event.add('summary', subject)
    event.add('dtstart', datetime.datetime.strptime(start_time_utc, "%d-%m-%Y %H:%M"))
    event.add('dtend', datetime.datetime.strptime(start_time_utc, "%d-%m-%Y %H:%M")+datetime.timedelta(hours=4))
    event.add('dtstamp', datetime.datetime.now().utcnow())
    event['uid'] = event_uid
    event.add('TZOFFSETFROM', datetime.timedelta(hours=3))
    event.add('TZOFFSETTO', datetime.timedelta(hours=3))
    event.add('TZID', 'Russian Standard Time')
    event.add('priority', 5)
    event.add('organizer', settings['organizer'])
    event.add('status', "confirmed")
    event.add('category', "Event")
    event.add('sequence', 1)
    event.add('X-MICROSOFT-DISALLOW-COUNTER', "TRUE")
    event.add('X-MICROSOFT-CDO-BUSYSTATUS', 'FREE')
    for current_attendee in attendees.split(","):
        event.add('attendee', current_attendee)
    alarm = icalendar.Alarm()
    alarm.add("action", "DISPLAY")
    alarm.add('description', "Reminder")
    alarm.add("TRIGGER;RELATED=START", "-PT15M")
    alarm.add('X-MICROSOFT-CDO-BUSYSTATUS', 'FREE')
    event.add_component(alarm)
    cal.add_component(event)

    cal_for_cancel = icalendar.Calendar()
    cal_for_cancel.add('prodid', '-//My calendar application//example.com//')
    cal_for_cancel.add('version', '2.0')
    cal_for_cancel.add('method', 'CANCEL')

    event_cancel = icalendar.Event()
    event_cancel.add('summary', "[CANCELLED] " + subject)
    event_cancel.add('dtstart', datetime.datetime.strptime(start_time_utc, "%d-%m-%Y %H:%M"))
    event_cancel.add('dtend', datetime.datetime.strptime(start_time_utc, "%d-%m-%Y %H:%M")+datetime.timedelta(hours=4))
    event_cancel.add('dtstamp', datetime.datetime.now().utcnow())
    event_cancel['uid'] = event_uid
    event_cancel.add('TZOFFSETFROM', datetime.timedelta(hours=3))
    event_cancel.add('TZOFFSETTO', datetime.timedelta(hours=3))
    event_cancel.add('TZID', 'Russian Standard Time')
    event_cancel.add('priority', 5)
    event_cancel.add('organizer', settings['organizer'])
    event_cancel.add('status', "cancelled")
    event_cancel.add('category', "Event")
    event_cancel.add('sequence', 1)
    event_cancel.add('X-MICROSOFT-DISALLOW-COUNTER', "TRUE")
    event_cancel.add('X-MICROSOFT-CDO-BUSYSTATUS', 'FREE')
    for current_attendee in attendees.split(","):
        event_cancel.add('attendee', current_attendee)

    cal_for_cancel.add_component(event_cancel)
    msg_for_cancel = MIMEMultipart("mixed")
    msg_for_cancel["Subject"] = "[CANCELLED] "  + subject
    msg_for_cancel["From"] = settings['e_mail_from']
    msg_for_cancel["To"] = attendees
    filename = "invite.ics"
    msg_a_for_cancel = MIMEMultipart('alternative')
    msg_for_cancel.attach(msg_a_for_cancel)
    part_calendar_for_cancel = MIMEMultipart('text', "calendar", method="CANCEL", name=filename)
    part_calendar_for_cancel.set_type('text/calendar; charset=UTF-8; method=CANCEL; component = VEVENT')
    part_calendar_for_cancel.set_payload(cal_for_cancel.to_ical())
    part_calendar_for_cancel.add_header('Content-Type', 'text/calendar')
    part_calendar_for_cancel.add_header('charset', 'UTF-8')
    part_calendar_for_cancel.add_header('component', 'VEVENT')
    part_calendar_for_cancel.add_header('method', 'CANCEL')
    part_calendar_for_cancel.add_header('Content-Description', filename)
    part_calendar_for_cancel.add_header('Content-ID', 'calendar_message')
    part_calendar_for_cancel.add_header("Content-class", "urn:content-classes:appointment")
    part_calendar_for_cancel.add_header("Filename", filename)
    part_calendar_for_cancel.add_header("Path", filename)

    # print(part_calendar_for_cancel)
    # exit()
    encode_base64(part_calendar_for_cancel)
    msg_a_for_cancel.attach(MIMEText(body.replace("please, perform this patching", "<font size=12 color='red'>DO NOT DO IT</font>"), 'html'))
    msg_a_for_cancel.attach(part_calendar_for_cancel)
    save_notification_to_disk=open("./archive/" + event_uid + ".msg", 'wb')
    save_notification_to_disk.write(msg_for_cancel.as_bytes())
    save_notification_to_disk.close()


    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = settings['e_mail_from']
    msg["To"] = attendees
    cursor_hashes_db.execute('INSERT INTO "HASHES" (HASH,EMAILS) VALUES (?,?)', (str(event_uid), attendees))
    connect_hashes_db.commit()


    msg_a = MIMEMultipart('alternative')
    msg.attach(msg_a)
    part_calendar = MIMEMultipart('text', "calendar", method="REQUEST", name=filename)
    part_calendar.set_type('text/calendar; charset=UTF-8; method=REQUEST; component = VEVENT')
    part_calendar.set_payload(cal.to_ical())
    part_calendar.add_header('Content-Type', 'text/calendar')
    part_calendar.add_header('charset', 'UTF-8')
    part_calendar.add_header('component', 'VEVENT')
    part_calendar.add_header('method', 'REQUEST')
    part_calendar.add_header('Content-Description', filename)
    part_calendar.add_header('Content-ID', 'calendar_message')
    part_calendar.add_header("Content-class", "urn:content-classes:appointment")
    part_calendar.add_header("Filename", filename)
    part_calendar.add_header("Path", filename)
    encode_base64(part_calendar)
    msg_a.attach(MIMEText(body, 'html'))
    msg_a.attach(part_calendar)
    recept_list=attendees.split(",")
    try:
        s = smtplib.SMTP(settings['smtp_server'])
        s.sendmail(msg["From"], recept_list, msg.as_string())
        s.quit()
        print("e-mail with '{title}' title has been sent successfully!".format(title=title))
    except Exception as e:
        termcolor.cprint("Error during sending an-email, second try...", color="white", on_color="on_red")
        try:
            s = smtplib.SMTP(settings['smtp_server'])
            print(recept_list)
            s.sendmail(msg["From"], recept_list, msg.as_string())
            s.quit()
            print("e-mail with '{title}' title has been sent successfully!".format(title=title))
        except Exception as e:
            termcolor.cprint("Can not send outlook-notofocation for this {prj} project to {start_date}".format(start_date=start_time, prj=title), color="white", on_color="on_red")
            print("Exceprion: {e}".format(e=str(e)))

def cancel_notification(hash):
    msg=open("./archive/" + hash + '.msg', 'rb').read().decode()


    recept_list = cursor_hashes_db.execute("SELECT EMAILS FROM HASHES WHERE HASH=:hash", {'hash' : hash}).fetchone()[0].split(',')

    s = smtplib.SMTP(settings['smtp_server'])
    s.sendmail(settings['e_mail_from'], recept_list, msg)
    s.quit()


def main():
    csv_files = glob.glob('./csv_files/*.csv')
    #example: {'25.12.2018 16:00': ['cent_os', 'cent_os_2']}
    uniq_datetime_dict_with_servers=extract_uniq_date_and_time_groups(csv_files)
    uniq_groups={}; extracted_data_from_xlsx=[]
    for current_uniq_datetime_dict_with_servers_key in uniq_datetime_dict_with_servers.keys():
        need_to_add_dba_team = False
        # example: {'UNIQ_PROJECT_NAME_1': ['server_1'], 'UNIQ_PROJECT_NAME_2': ['server_2', 'server_3']}
        uniq_groups=return_uniq_groups(uniq_datetime_dict_with_servers[current_uniq_datetime_dict_with_servers_key])
        for current_uniq_group_name_project_name, current_uniq_group_name_servers_list in uniq_groups.items():
            for current_uniq_group_name_servers in current_uniq_group_name_servers_list:
                if current_uniq_group_name_servers=='dba_needed':
                    need_to_add_dba_team=True
                    continue
                extracted_data_from_xlsx.append((return_information_from_xlsx_file(current_uniq_group_name_servers.lower()),current_uniq_group_name_servers))
        prepare_email(current_uniq_datetime_dict_with_servers_key, extracted_data_from_xlsx, current_uniq_group_name_project_name, need_to_add_dba_team)
        extracted_data_from_xlsx.clear()
        print("===========================================")

    connect_hashes_db.close()
    exit()


termcolor.cprint(" ,_     _\n |\\_,-~/\n / _  _ |    ,--.\n(  @  @ )   / ,-\'\n \  _T_/-._( (\n /         `. \ \n|         _  \ |\n \ \ ,  /      |\n  || |-_\__   /\n ((_/`(____,-\'", color="grey", on_color="on_white")

cursor_patching_db = sqlite3.connect('./patching.db').cursor()
connect_hashes_db=sqlite3.connect('./patching_hashes.db')
cursor_hashes_db=connect_hashes_db.cursor()

rfc_number=open('./rfc_number.txt', 'r').read().rstrip()
settings=get_settings()

patching_xlsx_file=openpyxl.load_workbook(filename='patching.xlsx', read_only=False, data_only=True)
sheet_with_schedule=patching_xlsx_file['Cycle_Patching']

args=parse_args()
if args.md5:
    cancel_notification(args.md5)
    exit()

main()
