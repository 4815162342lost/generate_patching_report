import csv
import datetime
from auto_mm import *

def snap_determine_needed_servers(db_cur,server_list):
    snapshots_for_servers_shich_should_be_created=[]
    for current_server in server_list:
        if db_cur.execute("SELECT NEED_SNAPSHOT FROM SERVERS WHERE SERVER_NAME=:server COLLATE NOCASE", {"server": current_server}).fetchone():
            snapshots_for_servers_shich_should_be_created.append(current_server)
    return snapshots_for_servers_shich_should_be_created

def snap_create_csv_file(db_cur, server_list, file_name, today):
    file_for_csv=open(file_name, 'w')
    csv_snapshots=csv.writer(file_for_csv, delimiter=';')
    for current_server in server_list:
        patching_code=db_cur.execute("SELECT WINDOW_CODE, START_TIME from SERVERS WHERE SERVER_NAME =:server COLLATE NOCASE", {"server": current_server}).fetchone()
        if not patching_code[0]:
            continue
        patching_start_date=get_patching_start_date(today, patching_code[0], db_cur)
        patching_total=datetime.datetime.combine(patching_start_date, datetime.time(int(patching_code[1].split(":")[0]), int(patching_code[1].split(":")[1])))
        csv_snapshots.writerow([current_server.lower(), patching_total.strftime("%d-%m-%Y %H:%M")])
    file_for_csv.close()
    print("Also csv-file {csv_file} for autoshapshoting has been created!".format(csv_file=file_name))
