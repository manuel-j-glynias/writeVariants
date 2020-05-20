import os
import mysql.connector
import datetime
from graphql_utils import replace_characters
from sql_helpers import get_one_jax_gene, preflight_ref, insert_editable_statement, insert_es_ref, get_loader_user_id
from sql_utils import get_local_db_connection, maybe_create_and_select_database, does_table_exist, drop_table_if_exists
import json


def write_one_reference(ref: dict,reference_dict:dict) -> (str,str):
    s = ''
    id = 'ref_' + str(ref['id'])
    title = ref['title']
    title = replace_characters(title)

    if not id in reference_dict:
        s = f'''{id} : createJaxReference(PMID: \\"{ref['pubMedId']}\\", id: \\"{id}\\", jaxId: \\"{str(ref['id'])}\\", shortReference: \\"{ref['url']}\\",title: \\"{title}\\"),'''
        reference_dict[id] = id
    return s, id

def get_list_of_files(path: str) -> list:
    json_files = []
    for entry in os.scandir(path):
        if entry.is_file():
            json_files.append(entry.path)
    return json_files


def read_one_variant_json(path:str)->dict:
    with open(path, 'r') as afile:
        variant_data = json.loads(afile.read())
        ckb_id = str(variant_data['id'])
        full_name = variant_data['fullName']
        variant_type = variant_data['impact']
        protein_effect = variant_data['proteinEffect']
        description = '-'
        if 'geneVariantDescriptions' in variant_data:
            descriptions_array = variant_data['geneVariantDescriptions']
            if len(descriptions_array) > 0:
                description: str = replace_characters(descriptions_array[0]['description'])
                references: list = descriptions_array[0]['references']

        gene_id = variant_data['gene']['id']
        gene = variant_data['gene']['geneSymbol']
        gDot = '-'
        cDot = '-'
        pDot = '-'
        transcript = '-'
        if 'referenceTranscriptCoordinates' in variant_data and variant_data['referenceTranscriptCoordinates'] != None:
            gDot = variant_data['referenceTranscriptCoordinates']['gDna']
            cDot = variant_data['referenceTranscriptCoordinates']['cDna']
            pDot = variant_data['referenceTranscriptCoordinates']['protein']
            transcript = variant_data['referenceTranscriptCoordinates']['transcript']

        variant = {
            'ckb_id':ckb_id,
            'name':full_name,
            'variant_type':variant_type,
            'protein_effect':protein_effect,
            'description':description,
            'references': references,
            'gene_id':gene_id,
            'gene':gene,
            'gDot':gDot,
            'cDot':cDot,
            'pDot':pDot,
            'transcript':transcript,
        }
        return variant

def get_variant_id_from_jax_id(jax_id: str) -> str:
    return 'v_' + jax_id


# createJaxVariant(
# cDot: String!
# gDot: String!
# id: ID!
# jaxId: String!
# name: String!
# pDot: String!
# proteinEffect: String!
# statement: String!
# transcript: String!
# variant_type: String!): String

def write_one_variant(variant: dict,gene_dict:dict,reference_dict:dict) -> str:
    id: str = get_variant_id_from_jax_id(variant['ckb_id'])
    gene_id = gene_dict[variant['gene']]

    s = f'''{id} : createJaxVariant(cDot: \\"{variant['cDot']}\\",gDot: \\"{variant['gDot']}\\", id: \\"{id}\\", jaxId: \\"{variant['ckb_id']}\\", name: \\"{variant['name']}\\",pDot: \\"{variant['pDot']}\\",proteinEffect: \\"{variant['protein_effect']}\\", statement: \\"{variant['description']}\\", transcript: \\"{variant['transcript']}\\",variant_type: \\"{variant['variant_type']}\\"),'''
    # addJaxVariantGene(gene: [ID!]!id: ID!): String
    s += f'''addJaxVariantGene(gene: [\\"{gene_id}\\"], id:\\"{id}\\"),'''
    if len(variant['references']) > 0:
        ref_array: str = '['
        for ref in variant['references']:
            m, ref_id = write_one_reference(ref, reference_dict)
            s += m
            ref_array += f'''\\"{ref_id}\\",'''
        ref_array += ']'
        #     addJaxGeneReferences(id: ID!references: [ID!]!): String

        s += f'''addJaxVariantReferences(id:\\"{id}\\", references:{ref_array}),'''
    return s

def create_jax_variant_table(my_cursor):
    table_name = 'jax_variant'
    if not does_table_exist(my_cursor, table_name):
        mySql_Create_Table_Query = 'CREATE TABLE jax_variant ( ' \
                                   'variantName varchar(100), ' \
                                   'description_id varchar(100), ' \
                                   'jax_Id varchar(100), ' \
                                   'jaxGene_gene_Id varchar(100), ' \
                                   'pDot varchar(100), ' \
                                   'cDot varchar(100), ' \
                                   'gDot varchar(100), ' \
                                   'transcript varchar(100), ' \
                                   'variantType varchar(100), ' \
                                   'proteinEffect varchar(100), ' \
                                'graph_id varchar(100) PRIMARY KEY, ' \
                                    'CONSTRAINT variant_description_fk_es_id FOREIGN KEY (description_id) REFERENCES editable_statements (graph_id), ' \
                                     'CONSTRAINT variant_fk_jax_gene FOREIGN KEY (jaxGene_gene_Id) REFERENCES jax_gene (graph_id) ' \
                                  ')'
        print(mySql_Create_Table_Query)
        result = my_cursor.execute(mySql_Create_Table_Query)
        print(f'{table_name} Table created successfully')

# variantName, description_id, jax_Id, jaxGene_gene_Id, pDot, cDot, gDot, transcript, variantType, proteinEffect, graph_id
def insert_jax_variant(my_cursor,name,description_id,jax_id,jax_gene_id,pdot,cdot,gdot,transcript,variant_type,protein_effect,graph_id):
    mySql_insert_query = "INSERT INTO jax_variant (variantName,description_id,jax_Id,jaxGene_gene_Id,pDot,cDot,gDot,transcript,variantType,proteinEffect,graph_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(name,description_id,jax_id,jax_gene_id,pdot,cdot,gdot,transcript,variant_type,protein_effect,graph_id))


def write_variants(my_db,my_cursor) -> None:
    json_files = get_list_of_files('data/variants')
    print("num variants=",len(json_files))
    loader_id = get_loader_user_id(my_cursor)
    counter = 0
    for json_file in json_files:
        variant: dict = read_one_variant_json(json_file)
        counter += 1
        if (counter % 100 == 0):
            print(counter)
        if variant is not None:
            # print(variant)
            id = 'jax_gene_' + str(variant['gene_id'])
            jax_dict = get_one_jax_gene(id,False,False,my_cursor)
            if jax_dict==None:
                print('none for ',id)
            else:
                graph_id = 'jaxVariant_' + str(variant['ckb_id'])
                gene_id = jax_dict['id']
                statement = variant['description']
                field: str = 'jaxVariantDescription_' + str(variant['ckb_id'])
                now = datetime.datetime.now()
                edit_date: str = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
                es_id: str = 'es_' + now.strftime("%Y%m%d%H%M%S%f")
                insert_editable_statement(my_cursor, field, statement, edit_date, loader_id, 'FALSE', es_id)
                insert_jax_variant(my_cursor, variant['name'], es_id, variant['ckb_id'], gene_id, variant['pDot'], variant['cDot'], variant['gDot'], variant['transcript'],
                                   variant['variant_type'], variant['protein_effect'], graph_id)
                for ref in variant['references']:
                    pmid = ref['pubMedId']
                    if pmid != None:
                        ref_id = preflight_ref(pmid, my_cursor)
                        if ref_id!=None:
                            insert_es_ref(my_cursor, es_id, ref_id)
                my_db.commit()


def create_jax_variant_db():
    print(datetime.datetime.now().strftime("%H:%M:%S"))
    server_read:str = 'localhost'

    my_db = None
    my_cursor = None
    try:
        my_db = get_local_db_connection()
        my_cursor = my_db.cursor(buffered=True)
        maybe_create_and_select_database(my_cursor, 'OmniSeqKnowledgebase')
        drop_table_if_exists(my_cursor,'jax_variant')
        create_jax_variant_table(my_cursor)
        write_variants(my_db,my_cursor)
    except mysql.connector.Error as error:
        print("Failed in MySQL: {}".format(error))
    finally:
        if (my_db.is_connected()):
            my_cursor.close()
    print(datetime.datetime.now().strftime("%H:%M:%S"))



def main():
    create_jax_variant_db()

if __name__ == "__main__":
    main()


