import mysql.connector


def get_cloud_db_connection():
    my_db = mysql.connector.connect(
        host="159.203.79.49",
        user="root",
        passwd="Omni2020"
    )
    return my_db


def get_local_db_connection():
    my_db = mysql.connector.connect(
        host="localhost",
        user="python_user",
        passwd="Omni2020"
    )
    return my_db


def drop_database(my_cursor,db_name):
    if does_db_exist(my_cursor,db_name):
        my_cursor.execute('DROP DATABASE ' + db_name)


def maybe_create_and_select_database(my_cursor, db_name):
    if not does_db_exist(my_cursor, db_name):
        my_cursor.execute('CREATE DATABASE ' + db_name)
        print(f"{db_name} Database created successfully")
    my_cursor.execute('USE ' + db_name)


def does_db_exist(my_cursor,db_name):
    exists = False
    my_cursor.execute("SHOW DATABASES")
    for x in my_cursor:
        if x[0].lower() == db_name.lower():
            exists = True
            break
    return exists


def does_table_exist(my_cursor,table_name):
    exists = False
    my_cursor.execute("SHOW TABLES")
    for x in my_cursor:
        if x[0] == table_name:
            exists = True
            break
    return exists

def drop_table_if_exists(my_cursor,table_name):
    sql = "DROP TABLE IF EXISTS " + table_name
    my_cursor.execute(sql)