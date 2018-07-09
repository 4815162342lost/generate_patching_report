#!/usr/bin/python3
import datetime
import csv
import smtplib
import glob
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sys
import os
from distutils.sysconfig import get_python_lib
import subprocess
import json
import logging

os.chdir(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(get_python_lib())

logging.basicConfig(level=logging.INFO, filemode="a", filename="/var/log/patching/patching_auto_snapshots.txt", datefmt="%d/%m%Y %H:%M:%S", format="%(asctime)s %(message)s")
sign = '<br>--------------------------------------------------------------------------------------------------------------------' \
       '<br><b>This message has been generated automatically!</b>'

logging.info("Starting the script...")

def get_settings():
    '''Function for get settings from txt-file and return dictionary'''
    settings={}
    exec(open("./settings_email.txt").read(), None, settings)
    return settings


def get_bitcoin_price():
    '''return current Bitcoin price. Just for fun'''
    logging.info("Let's know the current BTC proce...")
    import requests
    import json
    proxies={"http_proxy": settings["http_proxy"], "https_proxy" : settings["https_proxy"]}
    try:
        r=requests.get("https://blockchain.info/ticker", proxies=proxies)
        bitcoin_prise = json.loads(r.text)
        return str(int(bitcoin_prise["USD"]["15m"]))+ bitcoin_prise["USD"]["symbol"]
    except Exception as e:
        logging.warning("Critical error during BTC price returning: {exc}".format(exc=str(e)))
        try:
            logging.warning("Https status code: {code}; content: {content}".format(code=str(r.status_code), content=str(r.text)))
        except:
            logging.warning("Can not read https status code and content")
        return "unknown error"


def extract_needed_servers():
    '''function for read csv files and extract servers which should be patched between now+13 min. and now+28 min.'''
    servers_for_create_snapshot = {}
    logging.info("Searching needed servers...")
    csv_files=glob.glob('./*linux_snapshots*.csv')
    logging.info("Working with following csv-files: {csv}".format(csv=str(csv_files)))
    for csv_file_for_open in csv_files:
        csv_file = open(csv_file_for_open)
        min_start_time = datetime.datetime.now() + datetime.timedelta(minutes=13)
        max_start_time = datetime.datetime.now() + datetime.timedelta(minutes=28)
        patching_schedule_csv = csv.reader(csv_file, delimiter=';')
        for row in patching_schedule_csv:
            patching_start_time = datetime.datetime.strptime(row[1], '%d.%m.%Y %H:%M')
            if patching_start_time > min_start_time and patching_start_time < max_start_time:
                servers_for_create_snapshot[row[0]] = row[1]
        csv_file.close()
    logging.info("For these servers auto-snapshot will be created: {servers_snapshots}".format(servers_snapshots=servers_for_create_snapshot))
    return servers_for_create_snapshot

def create_snaphots(server_name):
    logging.info("Trying to create snapshot for {server} server".format(server=server_name))
    try:
        proc_create_snapshot=subprocess.Popen("sudo salt-cloud -y -a create_snapshot {server_name} snapshot_name='{RFC_number}' description='patching'\
         memdump=False quiesce=False --out=json".format(server_name=server_name.lower(), RFC_number=rfc_number), shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        std_out, std_err= proc_create_snapshot.communicate(timeout=360)
        json_std_out=json.loads(std_out)
    except subprocess.TimeoutExpired:
        proc_create_snapshot.kill()
        logging.critical("Salt-cloud timeout...")
        return (1, "salt-cloud process timeuot")
    if "Not Found" in list(json_std_out.keys()):
        logging.warning("Server in not found in VMWare Farm")
        return (1, "server is not found in VMWare Farm")
    try:
        snapshot_date=json_std_out[list(json_std_out.keys())[0]]["vmware"][server_name.lower()]["Snapshot created successfully"]["created"]
        logging.info("Snapshot created successfully. Snapshot's date: {snapshot_date}".format(snapshot_date=snapshot_date))
        return (0, snapshot_date)
    except Exception as e:
        logging.critical("Unknown error. Debug info: {debug}".format(debug=str(e)))
        return (1, 'Unknown error')


def email_sending(results_dic):
    logging.info("Prepare and send e-mail")
    mail_body="<html><head></head><body>Hello,<br><br> <b>Current date: </b> {date}<br><b>BTC price: </b>{btc}<br><br>".format(date=datetime.datetime.now().strftime("%d-%B-%Y, %H:%M"), btc=get_bitcoin_price())
    mail_body+="<table border='1'><tr><td>Server name</td><td>Created date</td></tr>"
    for current_result in results_dic.keys():
        mail_body+="<tr><td>{server_name}</td><td>{additional_info}</td></tr>".format(server_name=current_result, return_code=results_dic[current_result][0],
                                                                                                            additional_info=results_dic[current_result][1])
    mail_body+="</table>{sign}</body></html>".format(sign=sign)
    subject = '[Snapshots] RFC {rfc_number}: monthly Linux-patching'.format(rfc_number=rfc_number)
    msg = MIMEMultipart('related')
    msg_a = MIMEMultipart('alternative')
    msg.attach(msg_a)
    txt=''
    part1 = MIMEText(txt, 'plain')
    part2 = MIMEText(mail_body, 'html')
    msg_a.attach(part1)
    msg_a.attach(part2)
    msg['Subject'] = subject
    msg['From'] = settings['email_from']
    msg['To'] = settings['e_mail_to_snapshots']
    try:
        s = smtplib.SMTP(settings['smtp_server'])
        s.sendmail(msg['From'], settings['e_mail_to_snapshots'], msg.as_string())
        s.quit()
    except Exception as e:
        logging.critical("Critical error during sending e-mail. Additional info: {debug}".format(debug=str(e)))

settings=get_settings()
rfc_number=open('./rfc_number.txt', 'r').read().rstrip()
needed_servers=extract_needed_servers()
if needed_servers:
    salt_cloud_result={}
    for current_server in needed_servers:
        salt_cloud_result[current_server]=create_snaphots(current_server)
    email_sending(salt_cloud_result)
