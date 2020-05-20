import datetime
import json
import os
import mysql.connector
from sql_utils import does_table_exist, get_local_db_connection, maybe_create_and_select_database, drop_table_if_exists

GO_PATH: str = '/Users/mglynias/Documents/GitHub/writeVariants/data/GO_alterations'

def get_list_of_files(path: str) -> list:
    json_files = []
    for entry in os.scandir(path):
        if entry.is_file():
            json_files.append(entry.path)
    return json_files

def read_one_go_json(path:str)->dict:
    with open(path, 'r') as afile:
        go_data = json.loads(afile.read())
        results = go_data['results']
        return results

def get_all_jax_ids(my_cursor):
    query = 'SELECT jax_id,graph_id FROM OmniSeqKnowledgebase.jax_variant;'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    jax_dict = {}
    for row in rows:
        jax_dict[row[0]] = row[1]
    return jax_dict


def create_go_variant_table(my_cursor):
    table_name = 'go_variant'
    if not does_table_exist(my_cursor, table_name):
        mySql_Create_Table_Query = 'CREATE TABLE go_variant ( ' \
                                   'variantName varchar(100), ' \
                                   'geneName varchar(100), ' \
                                   'go_Id varchar(100), ' \
                                   'mutationType varchar(100), ' \
                                   'jaxVariant_Id varchar(100) DEFAULT NULL, ' \
                                'graph_id varchar(100) PRIMARY KEY, ' \
                                     'CONSTRAINT go_variant_fk_jax_variant FOREIGN KEY (jaxVariant_Id) REFERENCES jax_variant (graph_id) ' \
                                  ')'
        print(mySql_Create_Table_Query)
        result = my_cursor.execute(mySql_Create_Table_Query)
        print(f'{table_name} Table created successfully')


def insert_go_variant(my_cursor,variant_name,gene_name,go_id,mutationType,jax_variant_id,graph_id):
    mySql_insert_query = "INSERT INTO go_variant (variantName,geneName,go_Id,mutationType,jaxVariant_Id,graph_id) VALUES (%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(variant_name,gene_name,go_id,mutationType,jax_variant_id,graph_id))


def write_go_variants(my_db, my_cursor) -> None:
    json_files = get_list_of_files(GO_PATH)
    print("num files=", len(json_files))
    # loader_id = get_loader_user_id(my_cursor)
    counter = 0
    jax_dict = get_all_jax_ids(my_cursor)
    go_dict = {}
    for json_file in json_files:
        print(json_file)
        alteration_array = read_one_go_json(json_file)
        for alteration in alteration_array:
            if 'gene' in alteration:
                go_id = alteration['id']
                if not go_id in go_dict:
                    if 'mutation_type' in alteration:
                        mutation_type = alteration['mutation_type']
                    else:
                        mutation_type = ''
                    graph_id = 'go_variant_' + go_id
                    variant_name = alteration['name']
                    gene_name = alteration['gene']
                    jax_variant_id = None
                    if 'codes' in alteration:
                        for code in alteration['codes']:
                            print(code)
                            if code.startswith('JAX'):
                                jax_id = code[12:]
                                if jax_id in jax_dict:
                                    jax_variant_id = jax_dict[jax_id]
                                # variant_name,gene_name,go_id,mutationType,jax_variant_id,graph_id
                                break
                    print(variant_name, go_id, mutation_type, jax_variant_id, graph_id)
                    insert_go_variant(my_cursor, variant_name, gene_name, go_id, mutation_type, jax_variant_id,
                                      graph_id)
                    go_dict[go_id] = graph_id
                    counter += 1
                    if (counter % 100 == 0):
                        my_db.commit()
                        print(counter)
    my_db.commit()



def create_go_variant_db():
    print(datetime.datetime.now().strftime("%H:%M:%S"))
    my_db = None
    my_cursor = None
    try:
        my_db = get_local_db_connection()
        my_cursor = my_db.cursor(buffered=True)
        maybe_create_and_select_database(my_cursor, 'OmniSeqKnowledgebase')
        drop_table_if_exists(my_cursor,'go_variant')
        create_go_variant_table(my_cursor)
        write_go_variants(my_db,my_cursor)
    except mysql.connector.Error as error:
        print("Failed in MySQL: {}".format(error))
    finally:
        if (my_db.is_connected()):
            my_cursor.close()
    print(datetime.datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    create_go_variant_db()

