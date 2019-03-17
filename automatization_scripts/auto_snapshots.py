#!/usr/bin/python3
import datetime
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import sys
import os
from distutils.sysconfig import get_python_lib
import subprocess
import json
import logging
import dateutil.tz
import configparser
import argparse
import sqlite3
import time
import requests
import io

os.chdir(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(get_python_lib())

###################################################################################################################################################################################
logging.basicConfig(level=logging.INFO, filemode="a", filename="/var/log/patching/patching_auto_snapshots.txt", datefmt="%d/%m/%Y %H:%M:%S", format="%(asctime)s %(message)s")
#logging.basicConfig(level=logging.INFO, filemode="a", filename="/var/log/patching/patching_auto_snapshots_dev.txt", datefmt="%d/%m/%Y %H:%M:%S", format="%(asctime)s %(message)s")
sign = '<br>--------------------------------------------------------------------------------------------------------------------' \
       '<br><b>This message has been generated automatically!</b>'

logging.info("=======================================================================")
logging.info("Starting the script...")

def get_argparser():
    """Function for return list of servers from args"""
    args=argparse.ArgumentParser()
    args.add_argument("-s", '--servers', type=str, required=False, help='the list of servers separated by comma which require snapshot')
    args.add_argument("-a", '--auto_patching', type=str, required=False, help='the list of servers separated by comma which should patch automatically')
    return args.parse_args()


def get_settings():
    """parse the config file"""
    parse_conf=configparser.ConfigParser()
    parse_conf.read("./settings.cfg")
    return parse_conf['auto_snapshots']


def get_bitcoin_price():
    """return current Bitcoin price. Just for fun"""
    logging.info("Let's know the current BTC price...")
    proxies={"http": settings["http_proxy"], "https" : settings["https_proxy"]}
    try:
        r=requests.get("https://blockchain.info/ticker", proxies=proxies, timeout=30)
        bitcoin_prise = json.loads(r.text)
        return str(int(bitcoin_prise["USD"]["15m"]))+ bitcoin_prise["USD"]["symbol"]
    except Exception as e:
        logging.warning("Critical error during BTC price returning: {exc}".format(exc=str(e)))
        try:
            logging.warning("Https status code: {code}; content: {content}".format(code=str(r.status_code), content=str(r.text)))
        except:
            logging.warning("Can not read https status code and content")
        return "unknown error"


def get_eth_zec_price():
    """Return Ethereum and Zcash price. Why not?"""
    logging.info("Getting ETH and ZEC price")
    proxies={"http": settings["http_proxy"], "https" : settings["https_proxy"]}
    try:
        r=requests.get("https://min-api.cryptocompare.com/data/pricemulti?fsyms=ETH,ZEC&tsyms=USD", proxies=proxies, timeout=30)
        eth_zec_json=json.loads(r.text)
        return str(int(eth_zec_json['ETH']['USD'])) + "$", str(int(eth_zec_json['ZEC']['USD'])) + "$"
    except Exception as e:
        logging.warning("Can not get the ETH\ZEC price, exception: {exc}".format(exc=str(e)))
        try:
            logging.warning("Https status code: {code}; content: {content}".format(code=str(r.status_code), content=str(r.text)))
        except:
            logging.warning("Can not read https status code and content")
        finally:
            return ("unknown error","unknown error")

def get_nonexist_person():
    """Function for get non-exist person from https://thispersondoesnotexist.com/image site"""
    logging.info("Trying to get non-exists person from thispersondoesnotexist.com webiste")
    from PIL import Image
    headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:65.0) Gecko/20100101 Firefox/65.0"}
    proxies = {"http": settings["http_proxy"], "https": settings["https_proxy"]}
    try:
        pic_on_ram = requests.get('https://thispersondoesnotexist.com/image', headers=headers, proxies=proxies, timeout=30)
    except:
        logging.warning("Can not get image...")
        return 1
    logging.info("Opening and resizing image whic was downloaded successfully...")
    img = Image.open(io.BytesIO(pic_on_ram.content))
    resized_img = img.resize(size=(480, 480))
    file_obj = io.BytesIO()
    resized_img.save(file_obj, format='jpeg')
    return file_obj


def need_create_snapshot_or_not(servers):
    """Function which check need create snapshot or not from local sqlite3 database"""
    servers_which_require_snapshot=[]
    #################################################################################################################################
    sqlite3_database = sqlite3.connect("./patching.db")
#    sqlite3_database=sqlite3.connect("./patching_dev.db")
    sqlite3_database_cursor=sqlite3_database.cursor()
    for current_server in servers:
        try:
            if sqlite3_database_cursor.execute('SELECT NEED_SNAPSHOT FROM SERVERS WHERE SERVER_NAME=:server COLLATE NOCASE', {"server" : current_server}).fetchone()[0] == 1:
                logging.info("{server} server is require snapshot".format(server=current_server))
                servers_which_require_snapshot.append(current_server)
            # else:
            #     if current_server in servers_with_autopatching:
            #         output_database_cursor.execute("UPDATE AUTOMATIZATED_RESULTS SET SNAPSHOT_CREATED = 2 WHERE SERVER_NAME=:server_name", {'server_name': current_server})
        except Exception as e:
            logging.warning("Error during get info for {server} from sqlite3 database: {exception_text}".format(server=current_server, exception_text=e))
    return servers_which_require_snapshot



def create_snaphots(server_name):
    """Function for create snapshots"""
    logging.info("Trying to create snapshot for {server} server".format(server=server_name))
    try:
        proc_create_snapshot=subprocess.Popen("salt-cloud -y -a create_snapshot {server_name} snapshot_name='{RFC_number}' description='patching' memdump=False quiesce=False --out=json".format(server_name=server_name.lower(), RFC_number=rfc_number), shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        std_out, std_err= proc_create_snapshot.communicate(timeout=360)
        json_std_out=json.loads(std_out)
    except subprocess.TimeoutExpired:
        proc_create_snapshot.kill()
        logging.critical("Salt-cloud timeout...")
        return "salt-cloud process timeout"
    except Exception as e:
        logging.critical("Salt-cloud unknown error: {error}; std_out: {std_out}; std_error: {std_err}".format(error=str(e), std_out=std_out, std_err=std_err))
        return "salt-cloud unknown error"
    if "Not Found" in list(json_std_out.keys()):
        logging.warning("Server is not found in VMWare Farm")
        return "server is not found in VMWare Farm"
    try:
        snapshot_date=json_std_out[list(json_std_out.keys())[0]]["vmware"][server_name.lower()]["Snapshot created successfully"]["created"]
        logging.info("Snapshot created successfully. Snapshot's date: {snapshot_date}".format(snapshot_date=snapshot_date))
        utc_snapshot_date=datetime.datetime.strptime(snapshot_date, '%Y-%m-%d %H:%M:%S')
        utc_snapshot_date=utc_snapshot_date.replace(tzinfo=dateutil.tz.gettz('UTC'))
        cet_snapshot_date=utc_snapshot_date.astimezone(dateutil.tz.gettz('Europe/Paris'))
        # if server_name in servers_with_autopatching:
        #     output_database_cursor.execute("UPDATE AUTOMATIZATED_RESULTS SET SNAPSHOT_CREATED = 1 WHERE SERVER_NAME=:server_name",{'server_name': server_name})
        return str(datetime.datetime.strftime(cet_snapshot_date, '%Y-%m-%d %H:%M:%S'))
    except Exception as e:
        logging.critical("Unknown error. Debug info: {debug}; std_out: {std_out}; std_error: {std_err}".format(debug=str(e), std_out=std_out, std_err=std_err))
        return 'Unknown error, see logs'


def email_sending(results_dic):
    """Function for e-mail sending"""
    logging.info("Prepare and sending e-mail...")
    eth, zec = get_eth_zec_price()
    mail_body="<html><head></head><body><b>Current date: </b> {date} CET<br><b>BTC price: </b>{btc}<br> <b>ETH price: </b>{eth}<br> <b>ZEC price: </b>{zec}<br><br>".format(date=datetime.datetime.now().strftime("%d-%B-%Y, %H:%M"), btc=get_bitcoin_price(), eth=eth, zec=zec)
    mail_body+="<table border='1'><tr><td>Server name</td><td>Created date</td></tr>"
    for current_result in results_dic.keys():
        mail_body+="<tr><td>{server_name}</td><td>{additional_info}</td></tr>\n".format(server_name=current_result.upper(), additional_info=results_dic[current_result])
    mail_body+="</table><br><b>Random people which generated by <a href=https://thispersondoesnotexist.com>neuronets:</a></b><br><img src='cid:nonexist_people'>{sign}</body></html>".format(sign=sign)
    subject = '[Snapshots] RFC {rfc_number}: monthly Linux-patching'.format(rfc_number=rfc_number)
    msg = MIMEMultipart('related')
    msg_a = MIMEMultipart('alternative')
    msg.attach(msg_a)
    txt=''
    part1 = MIMEText(txt, 'plain')
    part2 = MIMEText(mail_body, 'html')
    nonexist_person =  get_nonexist_person()
    if nonexist_person != 1:
        nonexist_person.seek(0)
        part3=MIMEImage(nonexist_person.read(), _subtype="jpg")
        part3.add_header('Content-ID', '<nonexist_people>')
        msg.attach(part3)
    msg_a.attach(part1)
    msg_a.attach(part2)
    msg['Subject'] = subject
    msg['From'] = settings['email_from']
    msg['To'] = settings['e_mail_to']
    try:
        logging.info("Connecting to smtp-server...")
        s = smtplib.SMTP(settings['smtp_server'])
        s.sendmail(msg['From'], settings['e_mail_to'], msg.as_string())
        s.quit()
    except Exception as e:
        logging.critical("Critical error during sending e-mail. Additional info: {debug}".format(debug=str(e)))

settings = get_settings()
rfc_number=open('./rfc_number.txt', 'r').read().rstrip()

logging.info("Parse -s argument...")
arguments=get_argparser()

if arguments.servers:
    # output_database=sqlite3.connect("{database_locarion}{rfc_number}.db".format(rfc_number=rfc_number, database_locarion=settings['database_for_write_location']))
    # output_database_cursor=output_database.cursor()
    logging.info("Argument -s is not empty: {arg}".format(arg=arguments.servers))
    servers=arguments.servers.split(",")
    # servers_with_autopatching=[]
    # if arguments.auto_patching:
    #     servers_with_autopatching=arguments.auto_patching.split(',')
    salt_cloud_result = {}; servers_which_require_snapshots=[]
    servers_which_require_snapshots=need_create_snapshot_or_not(servers)
    if servers_which_require_snapshots:
        for current_server in servers_which_require_snapshots:
            salt_cloud_result[current_server] = create_snaphots(current_server)
        email_sending(salt_cloud_result)
    else:
        logging.info("There are no servers which require snapshots")
    logging.info("All done. Exiting...")
    # output_database.commit()
    # output_database.close()
    # if servers_with_autopatching:
    #     os.system("{script_autopatching}/autopatching.py -s {servers}".format(servers=','.join(servers_with_autopatching), script_autopatching=os.path.dirname(os.path.realpath(__file__))))
    # time.sleep(2)
#############################################################################################################################################################
    #time.sleep(300)
    exit()

logging.info("All done. Exiting...")
