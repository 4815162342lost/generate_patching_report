from auto_mm import *
from send_email import *
import logging
logging.getLogger(__name__)

def get_settings():
    settings={}
    exec(open('./settings.txt').read(), None, settings)
    return settings

def parcer():
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


def write_csv_total(csv_name, server_name, kernel_upgrade, reboot_required, counter):
    total_txt_file=open(csv_name, 'a')
    csv_writer=csv.writer(total_txt_file, delimiter=";")
    csv_writer.writerow((server_name, kernel_upgrade, reboot_required, counter))
    total_txt_file.close()


def perform_additional_actions(args, today, os, xlsx_name, settings, servers_for_patching):
    if args.csv == 'yes':
        import sqlite3
        import termcolor
        # open database or not
        db_con = sqlite3.connect('./patching.db')
        db_cur = db_con.cursor()
        logging.info("Raising working_with_csv finction")
        error_list_from_csv = working_with_csv(servers_for_patching, db_cur, today, os, args.csv, settings['timezone'])
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
