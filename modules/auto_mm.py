import csv
import calendar
import datetime

def working_with_csv(servers_for_patching, db_cur, today, os, need_csv_mm, need_csv_snapshot):
    '''Function for raise other function with csv-creation from auto_mm.py file'''
    servers_for_write_to_csv_mm, servers_with_additional_monitors, servers_for_write_to_csv_snapshots,\
    servers_for_write_to_csv_notify_before_4_days, error_list_from_csv = create_csv_list_with_servers_for_write_and_with_additional_monitors(servers_for_patching, db_cur, today)
    if need_csv_mm=='yes':
        write_to_csv('linux_MM_{date}_patching_{name}'.format(date=today.strftime("%b_%Y"), name=os), servers_for_write_to_csv_mm, 'long')
        print('Hey, csv-file linux_MM_{date}_patching_{name}.csv has been compiled!'.format(date=today.strftime("%b_%Y"), name=os))
        if servers_with_additional_monitors:
            write_to_csv('linux_MM_CIS_{date}_patching_{name}'.format(date=today.strftime("%b_%Y"), name=os),
                         servers_with_additional_monitors, "long")
            print("FYI: csv-file linux_MM_CIS_{date}_patching_{name}.csv created!".format(date=today.strftime("%b_%Y"), name=os))
        if servers_for_write_to_csv_notify_before_4_days:
            write_to_csv('linux_e_mail_notify_before_4_days_{date}_patching_{name}'.format(date=today.strftime("%b_%Y"), name=os), servers_for_write_to_csv_notify_before_4_days, 'short')
            print("FYI: csv-file linux_e_mail_notify_before_4_days_{date}_patching_{name}.csv created!".format(date=today.strftime("%b_%Y"), name=os))
    return error_list_from_csv

def get_patching_start_date(today, window_code, db_cur):
    '''function for return patching start date (year, minth and day)'''
    patch_code_from_db=db_cur.execute("SELECT IDX, WEEKDAY FROM WINDOW_CODE WHERE CODE =:window_code COLLATE NOCASE", {'window_code' : window_code }).fetchone()
    patch_month=today.month; patch_year=today.year;
    #if patchinh on first weekday -- get next month
    if not patch_code_from_db:
        return None
    if not patch_code_from_db[0]:
        patch_month=today.month+1
        if patch_month>12:
            patch_month=1; patch_year+=1
    cal=calendar.Calendar(firstweekday=6)
    calendar_for_month=cal.monthdayscalendar(patch_year, patch_month)
    #check day of week on first week or not
    if not calendar_for_month[0][patch_code_from_db[1]]:
        patch_day=calendar_for_month[patch_code_from_db[0]+1][patch_code_from_db[1]]
    else:
        patch_day = calendar_for_month[patch_code_from_db[0]][patch_code_from_db[1]]
    return datetime.datetime(year=patch_year, month=patch_month, day=patch_day)

def get_patching_end_date_and_time(patching_start_date, patching_start_time, patching_duration):
    '''function for return patching end date and time'''
    patching_start_datetime=datetime.datetime(year=patching_start_date.year, month=patching_start_date.month, day=patching_start_date.day, hour=int(patching_start_time[0:2]), minute=int(patching_start_time[3:]))
    patchng_end_datetime=patching_start_datetime + datetime.timedelta(hours=int(patching_duration[0:2]), minutes=int(patching_duration[3:]))
    return patchng_end_datetime

def write_to_csv(csv_name, list_for_write, csv_format):
    '''function for generate csv-files'''
    responsible_user='Ilyas Ganiev'
    action='schedule'
    comment='patching'
    with open(str(csv_name) + '.csv', 'w') as csv_mm:
        csv_mm_writer=csv.writer(csv_mm, delimiter=';')
        if csv_format=='long':
            csv_mm_writer.writerow(['action','start_downtime','end_downtime','comment','responsible_user','host','service'])
            for current_list_for_write in list_for_write:
                csv_mm_writer.writerow([action, current_list_for_write[1], current_list_for_write[2], comment, responsible_user, current_list_for_write[0], current_list_for_write[3]])
        else:
            for current_list_for_write in list_for_write:
                csv_mm_writer.writerow([current_list_for_write[0], current_list_for_write[1]])

def create_csv_list_with_servers_for_write_and_with_additional_monitors(servers_for_patching, db_cur, today):
    '''return list with mm plan'''
    servers_for_write_to_csv=[]; servers_with_additional_monitors=[]; error_list=[]; snapshots_list=[]; servers_before_4_days=[]
    for current_server in servers_for_patching:
        server_window_code, need_mm, need_snapshot, need_email_before_four_days= db_cur.execute('SELECT WINDOW_CODE, NEED_MM, NEED_SNAPSHOT, NEED_EMAIL_BEFORE_4_DAYS FROM SERVERS \
                                            WHERE SERVER_NAME=:current_server COLLATE NOCASE',
                                            {'current_server':current_server}).fetchone()
        if not server_window_code:
            error_list.append('Server {server} does not exist on database...'.format(server=current_server))
            continue
        if need_mm==0:
            print("For server {server} maintenance mode is not required... Skip it")
            continue
        #get patching start day
        patching_start_date=get_patching_start_date(today, server_window_code, db_cur)
        server_name_from_db, patching_start_time, patching_duration, additional_monitors=db_cur.execute('SELECT SERVER_NAME, START_TIME, DURATION_TIME, ADDITIONAL_MONITORS FROM SERVERS\
                                                               WHERE SERVER_NAME=:current_server COLLATE NOCASE',
                                                              {'current_server' : current_server}).fetchone()
        patching_start_datetime=datetime.datetime(year=patching_start_date.year, month=patching_start_date.month, day=patching_start_date.day, hour=int(patching_start_time[0:2]), minute=int(patching_start_time[3:]))
        patching_end_datetine=get_patching_end_date_and_time(patching_start_date, patching_start_time, patching_duration)
        servers_for_write_to_csv.append((server_name_from_db, patching_start_datetime.strftime('%d.%m.%Y %H:%M'), patching_end_datetine.strftime('%d.%m.%Y %H:%M'), ''))
        if need_snapshot==1:
            snapshots_list.append((server_name_from_db, patching_start_datetime.strftime('%d.%m.%Y %H:%M')))
        if need_email_before_four_days==1:
            servers_before_4_days.append((server_name_from_db, patching_start_datetime.strftime('%d.%m.%Y %H:%M')))
        if additional_monitors == 1:
            additional_cis =db_cur.execute('SELECT ADDITIONAL_CIS, ADITIONAL_MONITOR_NAME FROM ADDITIONAL_MONITORS\
                           WHERE SERVER_NAME=:current_server COLLATE NOCASE',
                           {'current_server' : current_server}).fetchall()
            if not additional_cis:
                error_list.append("Error: For server {server_name} should be additional monitors...".format(server_name=current_server))
                continue
            for current_cis in additional_cis:
                servers_with_additional_monitors.append((current_cis[0], patching_start_datetime.strftime('%d.%m.%Y %H:%M'), patching_end_datetine.strftime('%d.%m.%Y %H:%M'), current_cis[1]))
    return servers_for_write_to_csv, servers_with_additional_monitors, snapshots_list, servers_before_4_days, error_list
