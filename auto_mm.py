#!/usr/bin/python3
import csv
import datetime
import calendar

def get_patching_start_date(today, window_code, db_cur):
    '''function for return patching start date (year, minth and day)'''
    patch_code_from_db=db_cur.execute("SELECT IDX, WEEKDAY FROM WINDOW_CODE WHERE CODE =:window_code COLLATE NOCASE", {'window_code' : window_code }).fetchone()
    patch_month=today.month; patch_year=today.year;
    #if patchinh on first weekday -- get next month
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

def write_to_csv(month, cis_mm_plan):
    '''function for write csv file with maintenance mode'''
    responsible_user='Ilya G'
    action='schedule'
    comment='patching'
#action;start_downtime;end_downtime;comment;responsible_user;host;service
    with open(str(month) + '_security_patching_mm.csv', 'w') as csv_mm:
        csv_mm_writer=csv.writer(csv_mm, delimiter=';')
        csv_mm_writer.writerow(['action','start_downtime','end_downtime','comment','responsible_user','host','service',''])
        for current_cis_mm in cis_mm_plan:
            csv_mm_writer.writerow([action, current_cis_mm[1], current_cis_mm[2], comment, responsible_user, current_cis_mm[0], current_cis_mm[3]])


def create_csv_list_with_servers_for_write_and_with_additional_monitors(servers_for_patching, db_cur, today):
    '''return list with mm plan'''
    servers_for_write_to_csv=[]
    servers_with_additional_monitors=[]
    for current_server in servers_for_patching:
        server_window_code= db_cur.execute('SELECT WINDOW_CODE FROM SERVERS \
                                            WHERE SERVER_NAME=:current_server COLLATE NOCASE',
                                            {'current_server':current_server}).fetchone()
        #get patching start day
        patching_start_date=get_patching_start_date(today, server_window_code[0], db_cur)
        server_name_from_db, patching_start_time, patching_duration, additional_monitors=db_cur.execute('SELECT SERVER_NAME, START_TIME, DURATION_TIME, ADDITIONAL_MONITORS FROM SERVERS\
                                                               WHERE SERVER_NAME=:current_server COLLATE NOCASE',
                                                              {'current_server' : current_server}).fetchone()
        patching_start_datetime=datetime.datetime(year=patching_start_date.year, month=patching_start_date.month, day=patching_start_date.day, hour=int(patching_start_time[0:2]), minute=int(patching_duration[3:]))
        patching_end_datetine=get_patching_end_date_and_time(patching_start_date, patching_start_time, patching_duration)
        servers_for_write_to_csv.append((server_name_from_db, patching_start_datetime.strftime('%d.%m.%Y %H:%M'), patching_end_datetine.strftime('%d.%m.%Y %H:%M'), ''))
        if additional_monitors == 1:
            print(current_server)
            additional_cis =db_cur.execute('SELECT ADDITIONAL_CIS, ADITIONAL_MONITOR_NAME FROM ADDITIONAL_MONITORS\
                           WHERE SERVER_NAME=:current_server COLLATE NOCASE',
                           {'current_server' : current_server}).fetchall()
            for current_cis in additional_cis:
                servers_with_additional_monitors.append((current_cis[0], patching_start_datetime.strftime('%d.%m.%Y %H:%M'), patching_end_datetine.strftime('%d.%m.%Y %H:%M'), current_cis[1]))
    return servers_for_write_to_csv, servers_with_additional_monitors

