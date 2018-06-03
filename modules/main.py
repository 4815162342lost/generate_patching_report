from auto_mm import *
from auto_snapshots import *
from send_email import *

def get_settings():
    settings={}
    exec(open('./settings.txt').read(), None, settings)
    return settings

def parcer():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-e", "--email", type=str, required=False, help="Enter your e-mail")
    parser.add_argument("-c", "--csv", type=str, required=False, default='no',
                        help="create csv-file with maintenance mode schedule or not ('yes' or 'no'), default -- 'no'")
    parser.add_argument("-s", "--snap", type=str, required=False, default='no', help="create csv-file for snapshots creation or not")
    args = parser.parse_args()
    return args

def perform_additional_actions(args, today, os, xlsx_name, settings, servers_for_patching):
    if args.csv == 'yes' or args.snap == 'yes':
        import sqlite3
        import termcolor
        # open database or not
        db_con = sqlite3.connect('./patching.db')
        db_cur = db_con.cursor()
    else:
        return 0
    if args.csv=='yes':
        error_list_from_csv = working_with_csv(servers_for_patching, db_cur, today, os)
        if error_list_from_csv:
            termcolor.cprint("Maintenance mode will be incorrect:\n" + ',\n'.join(error_list_from_csv), color='magenta', on_color='on_white')
    if args.snap=='yes':
        servers_whcih_require_snap_without_additional_activities=snap_determine_needed_servers(db_cur, servers_for_patching)
        snap_create_csv_file(db_cur, servers_whcih_require_snap_without_additional_activities, "auto-snapshots_{os}_{month}.csv".format(month=today.strftime("%B"), os=os), today)
    db_con.close()
    if args.email != None:
        send_mail(args.email, settings['email_from'], settings['smtp_server'],  xlsx_name, today, 'Patching list for {os} '.format(os=os))
        print("All done, the file \"{file_name}\" has been sent to e-mail {mail_address}".format(file_name=xlsx_name, mail_address=args.email))
    else:
        print("All done. Please, see the file \"" + xlsx_name + "\". Have a nice day!")
