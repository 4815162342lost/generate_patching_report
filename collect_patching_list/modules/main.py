from auto_mm import *
from send_email import *
import logging
logging.getLogger(__name__)
import configparser

def get_settings():
    '''parse the config file'''
    parse_conf=configparser.ConfigParser()
    parse_conf.read("./settings.cfg")
    return parse_conf['collect_patching_list']


def parcer():
    '''parse the arguments from command line options and return'''
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", type=str, required=False, help="Enter your e-mail")
    parser.add_argument("-c", "--csv", type=str, required=False, default='no',
                        help="create csv-file with maintenance mode\ autosending e-mails\ autocreate snapshots, default -- 'no', can be yes or no")
    parser.add_argument("-n", '--nocheck', type=str, required=False, help="do not check updates, just generate csv-files only", default="no")
    parser.add_argument("-d", '--debug', type=str, required=False, help='run with debug mode', default='no')
    args = parser.parse_args()
    logging.info("Input arguments: {args}".format(args=str(args)))
    return args


#python3 on Centos7 is so old...
#def write_csv_total(csv_name, server_name, kernel_upgrade, reboot_required, counter, *column_width):
def write_csv_total(csv_writer, server_name, kernel_upgrade, reboot_required, counter, column_width):
    '''write to total.csv file'''
    csv_writer.writerow((server_name, kernel_upgrade, reboot_required, counter, column_width[0], column_width[1], column_width[2]))


def return_csv_for_total(month_year):
    '''return total.csv file for current month'''
    import os
    #if total.csv does not exists
    if not os.path.exists('./' + month_year + '_separate_csv_with_patching_list/total.csv'):
        #try to create total.csv file
        try:
            total_csv_file=open('./' + month_year + '_separate_csv_with_patching_list/total.csv', 'a')
        #create subdirectory if does not exists
        except FileNotFoundError:
            os.makedirs('./' + month_year + '_separate_csv_with_patching_list')
            total_csv_file = open('./' + month_year + '_separate_csv_with_patching_list/total.csv', 'a')
        print('./' + month_year + '_separate_csv_with_patching_list/ directory has been created!')
        csv_writer_total=csv.writer(total_csv_file, delimiter=";")
        csv_writer_total.writerow(("Server_name", "need_kernel_upgrade", "reboot_required", "updates_count", "column0_width", "column1_width", "column2_width"))
    else:
        print(month_year + '_separate_csv_with_patching_list/total.csv already exists, just append to file')
        total_csv_file=open('./' + month_year + '_separate_csv_with_patching_list/total.csv', 'a')
        csv_writer_total=csv.writer(total_csv_file, delimiter=";")
    return csv_writer_total


def return_csv_file_for_single_host(server_name, month_year):
    '''return csv-object for single host'''
    csv_file_for_server=open('./' + month_year + '_separate_csv_with_patching_list/' + server_name, 'w')
    csv_writer=csv.writer(csv_file_for_server, delimiter=';')
    csv_writer.writerow(("Package name", 'Current version', 'Available version'))
    return csv_writer


def perform_additional_actions(args, today, os, xlsx_name, settings, servers_for_patching):
    if args.csv == 'yes':
        import sqlite3
        import termcolor
        # open database or not
        db_con = sqlite3.connect('./patching.db')
        db_cur = db_con.cursor()
        logging.info("Raising working_with_csv finction")
        error_list_from_csv = working_with_csv(servers_for_patching, db_cur, today, os, settings['timezone'])
        logging.info("Error list in csv-ffile: {error_list}".format(error_list=error_list_from_csv))
        if error_list_from_csv:
            termcolor.cprint("Maintenance mode will be incorrect:\n" + ',\n'.join(error_list_from_csv), color='magenta', on_color='on_white')
        db_con.close()
    if args.email != None:
        logging.info("Sending e-mail to {e_mail}".format(e_mail=args.email))
        send_mail(args.email, settings['email_from'], settings['smtp_server'],  xlsx_name, today, 'Patching list for {os} '.format(os=os))
        print("All done, the file \"{file_name}\" has been sent to e-mail {mail_address}".format(file_name=xlsx_name,
mail_address=args.email))
    else:
        print("All done. Please, see the file \"" + xlsx_name + "\". Have a nice day!")
