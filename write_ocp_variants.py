import xlrd
import mysql.connector
import datetime
from graphql_utils import replace_characters, send_mutation, send_query, get_reference_from_pmid_by_metapub, \
    get_authors_names, fix_author_id, ref_name_from_authors_pmid_and_year
from sql_helpers import get_one_jax_gene, insert_editable_statement, get_loader_user_id
from sql_utils import get_local_db_connection, maybe_create_and_select_database, does_table_exist, drop_table_if_exists


def create_ocp_variant_table(my_cursor):
    table_name = 'ocp_variant'
    if not does_table_exist(my_cursor, table_name):
        mySql_Create_Table_Query = 'CREATE TABLE ocp_variant ( ' \
                                   'variantName varchar(100), ' \
                                   'omniGene_gene_Id varchar(100), ' \
                                   'description_id varchar(100), ' \
                                   'pDot varchar(100), ' \
                                   'cDot varchar(100), ' \
                                   'gDot varchar(100), ' \
                                   'regionType varchar(100), ' \
                                   'indelType varchar(100), ' \
                                   'variantType varchar(100), ' \
                                   'variantProteinEffect varchar(100), ' \
                                   'jax_variant_Id varchar(100) DEFAULT NULL, ' \
                                   'go_variant_Id varchar(100) DEFAULT NULL, ' \
                                   'clinvar_variant_Id varchar(100) DEFAULT NULL, ' \
                                   'hot_spot_variant_Id varchar(100) DEFAULT NULL, ' \
                                   'exon varchar(100) , ' \
                                   'graph_id varchar(100) PRIMARY KEY, ' \
                                   'CONSTRAINT ocp_variant_description_fk_es_id FOREIGN KEY (description_id) REFERENCES editable_statements (graph_id), ' \
                                   'CONSTRAINT ocp_variant_fk_omni_gene FOREIGN KEY (omniGene_gene_Id) REFERENCES omnigene (graph_id), ' \
                                   'CONSTRAINT ocp_variant_fk_jax_variant FOREIGN KEY (jax_variant_Id) REFERENCES jax_variant (graph_id), ' \
                                   'CONSTRAINT ocp_variant_fk_go_variant FOREIGN KEY (go_variant_Id) REFERENCES go_variant (graph_id), ' \
                                   'CONSTRAINT ocp_variant_fk_clinvar_variant FOREIGN KEY (clinvar_variant_Id) REFERENCES clinvar (graph_id), ' \
                                   'CONSTRAINT ocp_variant_fk_hot_spot_variant FOREIGN KEY (hot_spot_variant_Id) REFERENCES hot_spot (graph_id) ' \
                                   ')'
        print(mySql_Create_Table_Query)
        result = my_cursor.execute(mySql_Create_Table_Query)
        print(f'{table_name} Table created successfully')

def insert_ocp_variant(my_cursor,name,omnigene_id,description_id, pdot,cdot,gdot,regionType,indelType,variantType,variantProteinEffect,
                       jax_variant_id,go_variant_Id,clinvar_variant_Id, hot_spot_variant_Id, exon,graph_id):
    if jax_variant_id =='':
        jax_variant_id = None
    if go_variant_Id =='':
        go_variant_Id = None
    if clinvar_variant_Id =='':
        clinvar_variant_Id = None
    if hot_spot_variant_Id =='':
        hot_spot_variant_Id = None

    mySql_insert_query = "INSERT INTO ocp_variant (variantName,omniGene_gene_Id,description_id,pDot,cDot,gDot,regionType,indelType,variantType,variantProteinEffect,jax_variant_Id,go_variant_Id,clinvar_variant_Id,hot_spot_variant_Id,exon,graph_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(name,omnigene_id,description_id, pdot,cdot,gdot,regionType,indelType,variantType,variantProteinEffect,jax_variant_id,
                                                   go_variant_Id,clinvar_variant_Id, hot_spot_variant_Id,exon,graph_id))


def get_omnigene_id_from_name(my_cursor,gene_name):
    id = ''
    query = f'SELECT graph_id FROM OmniSeqKnowledgebase.omnigene where name="{gene_name}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row != None:
        id = row[0]
    return id


def get_jax_variant_id_from_name(my_cursor,variant_name):
    id = ''
    protein_effect = ''
    cdot = ''
    gdot = ''
    description = ''
    query = f'SELECT jax.graph_id, jax.proteinEffect, jax.cDot, jax.gDot,es.statement FROM OmniSeqKnowledgebase.jax_variant jax INNER JOIN OmniSeqKnowledgebase.editable_statements es ON jax.description_id = es.graph_id where jax.variantName="{variant_name}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row != None:
        id = row[0]
        protein_effect= row[1]
        cdot = row[2]
        gdot = row[3]
        description = row[4]
    return id,protein_effect,cdot,gdot,description


def get_go_variant_id_from_jax(my_cursor,jax_variant_id):
    id = ''
    query = f'SELECT graph_id FROM OmniSeqKnowledgebase.go_variant where jaxVariant_Id="{jax_variant_id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row != None:
        id = row[0]
    return id

def get_clinvar_variant_from_gene_and_pdot(my_cursor,gene,pdot):
    id = ''
    query = f'SELECT graph_id FROM OmniSeqKnowledgebase.clinvar where gene="{gene}" and pDot="{pdot}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row != None:
        id = row[0]
    return id

def get_hot_spot_variant_from_variant_name(my_cursor,variant_name):
    id = ''
    query = f'SELECT graph_id FROM OmniSeqKnowledgebase.hot_spot where hs_name="{variant_name}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row != None:
        id = row[0]
    return id


def write_ocp_variants(my_db, my_cursor):
    loader_id = get_loader_user_id(my_cursor)
    wb = xlrd.open_workbook(filename='data/OCP_Lev1_2_Variants_w_exon.xlsx')
    sheet = wb.sheet_by_index(0)
    counter = 0
    for row_idx in range(1, sheet.nrows):
        gene_name = sheet.cell_value(row_idx, 0)
        variantName = sheet.cell_value(row_idx, 1)
        copyChange = sheet.cell_value(row_idx, 3)
        fusionDesc = sheet.cell_value(row_idx, 4)
        regionType = sheet.cell_value(row_idx, 9)
        regionAAChange = sheet.cell_value(row_idx, 13)
        regionIndelType= sheet.cell_value(row_idx, 14)
        exon = sheet.cell_value(row_idx, 18)
        pdot = ''
        if fusionDesc != '':
            variantType = 'Fusion'
            pdot = 'fusion'
        elif copyChange != '':
            variantType = 'CNV'
            pdot = copyChange
        elif regionIndelType != '':
            variantType = 'Indel'
            pdot = regionAAChange
        elif regionAAChange != '':
            variantType = 'SNV'
            pdot = regionAAChange
        else:
            variantType = None
        if (variantType != None):
            omnigene_id = get_omnigene_id_from_name(my_cursor,gene_name)
            gene_plus_pdot = gene_name + ' ' + pdot

            jax_variant_id,protein_effect,cdot,gdot,description = get_jax_variant_id_from_name(my_cursor,variantName)
            go_variant_id = get_go_variant_id_from_jax(my_cursor,jax_variant_id)
            cv_variant_id = get_clinvar_variant_from_gene_and_pdot(my_cursor,gene_name,pdot)
            hs_variant_id = get_hot_spot_variant_from_variant_name(my_cursor,gene_plus_pdot)
            # print(variantType,gene_name,omnigene_id,variantName,jax_variant_id,description)
            graph_id = 'ocpVariant_' + str(counter).zfill(3);
            field: str = 'ocpVariantDescription_' + str(counter)
            now = datetime.datetime.now()
            edit_date: str = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
            es_id: str = 'es_' + now.strftime("%Y%m%d%H%M%S%f")
            insert_editable_statement(my_cursor, field, description, edit_date, loader_id, 'FALSE', es_id)

            insert_ocp_variant(my_cursor,gene_plus_pdot,omnigene_id,es_id,pdot,cdot,gdot,regionType,regionIndelType,variantType,protein_effect,
                               jax_variant_id,go_variant_id,cv_variant_id, hs_variant_id,exon,graph_id)
            counter += 1
            if (counter % 100 == 0):
                print(counter)
    my_db.commit()


def create_ocp_variant_db():
    print(datetime.datetime.now().strftime("%H:%M:%S"))

    my_db = None
    my_cursor = None
    try:
        my_db = get_local_db_connection()
        my_cursor = my_db.cursor(buffered=True)
        maybe_create_and_select_database(my_cursor, 'OmniSeqKnowledgebase')
        drop_table_if_exists(my_cursor, 'ocp_variant')
        create_ocp_variant_table(my_cursor)
        write_ocp_variants(my_db, my_cursor)
    except mysql.connector.Error as error:
        print("Failed in MySQL: {}".format(error))
    finally:
        if (my_db.is_connected()):
            my_cursor.close()
    print(datetime.datetime.now().strftime("%H:%M:%S"))

if __name__ == "__main__":
    create_ocp_variant_db()
