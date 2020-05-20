import mysql.connector
import datetime
import populate_from_sql
from graphql_utils import erase_neo4j
from sql_utils import get_local_db_connection, maybe_create_and_select_database


def build_graphql_from_sql():
    print(datetime.datetime.now().strftime("%H:%M:%S"))

    schema_graphql = 'schema.graphql'
    server_write:str = 'localhost'

    my_db = None
    my_cursor = None
    # erase_neo4j(schema_graphql, server_write)
    try:
        my_db = get_local_db_connection()
        my_cursor = my_db.cursor(buffered=True)
        maybe_create_and_select_database(my_cursor, 'OmniSeqKnowledgebase')
        populate_from_sql.write_authors(my_cursor, server_write)
        populate_from_sql.write_journals(my_cursor, server_write)
        populate_from_sql.write_references(my_cursor, server_write)

        populate_from_sql.write_internet_references(my_cursor, server_write)
        populate_from_sql.write_users(my_cursor, server_write)

        populate_from_sql.write_editable_statements(my_cursor, server_write)

        populate_from_sql.write_jax_genes(my_cursor, server_write)
        populate_from_sql.write_mygene_genes(my_cursor, server_write)
        populate_from_sql.write_uniprot(my_cursor, server_write)

        populate_from_sql.write_omnigene(my_cursor, server_write)
        populate_from_sql.write_jax_variants(my_cursor, server_write)
        populate_from_sql.write_hot_spot_variants(my_cursor, server_write)
        populate_from_sql.write_clinvar_variants(my_cursor, server_write)
        populate_from_sql.write_go_variants(my_cursor, server_write)
        populate_from_sql.write_ocp_variants(my_cursor, server_write)
    except mysql.connector.Error as error:
        print("Failed in MySQL: {}".format(error))
    finally:
        if (my_db.is_connected()):
            my_cursor.close()
    print(datetime.datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    build_graphql_from_sql()