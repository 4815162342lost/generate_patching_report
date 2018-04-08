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
    args = parser.parse_args()
    return args

def sqlite(csv):
    if csv == 'yes':
        import sqlite3
        # open database or not
        db_con = sqlite3.connect('./patching.db')
        db_cur = db_con.cursor()
        return db_cur
    else:
        return None
