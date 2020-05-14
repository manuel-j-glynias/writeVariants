import json
import csv
import mysql.connector
from sql_utils import does_table_exist, get_local_db_connection, drop_table_if_exists, maybe_create_and_select_database


def read_snv_hotspot(onco_dict):
    hot_spots = []
    with open('data/hotspots_v2/SNV-hotspots-Table 1.tsv') as tsvfile:
        reader = csv.DictReader(tsvfile, dialect='excel-tab')
        for row in reader:
            # print(row)
            gene = row['Hugo_Symbol']
            referenceAminoAcid = row['Reference_Amino_Acid'].split(':')[0]
            variantAminoAcid = row['Variant_Amino_Acid'].split(':')[0]
            begin = row['Amino_Acid_Position']
            if not begin.isnumeric():
                position = 0
            else:
                position = int(begin)
            if referenceAminoAcid == 'splice':
                name = gene + ' ' + begin
            else:
                name = gene +  ' ' + referenceAminoAcid + begin + variantAminoAcid

            occurrences = handle_occurrences(row['Detailed_Cancer_Types'],onco_dict)
            hot_spot = {'name':name, 'gene':gene,
                        'referenceAminoAcid':referenceAminoAcid,
                        'variantAminoAcid':variantAminoAcid,
                        'begin':begin,
                        'end':begin,
                        'position':position,
                        'occurrences':occurrences}
            hot_spots.append(hot_spot)
    return hot_spots

def read_indel_hotspot(onco_dict):
    hot_spots = []
    with open('data/hotspots_v2/INDEL-hotspots-Table 1.tsv') as tsvfile:
        reader = csv.DictReader(tsvfile, dialect='excel-tab')
        for row in reader:
            # print(row)
            gene = row['Hugo_Symbol']

            variant = row['Variant_Amino_Acid'].split(':')[0]
            name = gene + ' ' + variant
            referenceAminoAcid = variant[:1]
            variantAminoAcid = ''
            if '_' in variant:
                variantAminoAcid = variant.split('_')[1][:1]
            if '-' in row['Amino_Acid_Position']:
                pos = row['Amino_Acid_Position'].split('-')
                begin = pos[0]
                end = pos[1]
            else:
                begin = row['Amino_Acid_Position']
                end = begin
            position = int(begin)
            if position < 0:
                position = 0

            occurrences = handle_occurrences(row['Detailed_Cancer_Types'],onco_dict)
            hot_spot = {'name':name, 'gene':gene,
                        'referenceAminoAcid':referenceAminoAcid,
                        'variantAminoAcid':variantAminoAcid,
                        'begin':begin,
                        'end':end,
                        'position':position,
                        'occurrences':occurrences}
            hot_spots.append(hot_spot)
    return hot_spots

def create_hot_spot_table(my_cursor):
    table_name = 'hot_spot'
    if not does_table_exist(my_cursor, table_name):
        mySql_Create_Table_Query = 'CREATE TABLE hot_spot ( ' \
                                   'hs_name varchar(100), ' \
                                   'gene varchar(100), ' \
                                   'referenceAminoAcid varchar(10), ' \
                                   'variantAminoAcid varchar(10), ' \
                                   'hs_begin varchar(100), ' \
                                   'hs_end varchar(100), ' \
                                   'hs_position MEDIUMINT, ' \
                                'graph_id varchar(100) PRIMARY KEY ' \
                                  ')'
        print(mySql_Create_Table_Query)
        result = my_cursor.execute(mySql_Create_Table_Query)
        print(f'{table_name} Table created successfully')

def insert_hotspot(my_cursor,hot_spot,graph_id):

    mySql_insert_query = "INSERT INTO hot_spot (hs_name,gene,referenceAminoAcid,variantAminoAcid,hs_begin,hs_end,hs_position,graph_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(hot_spot['name'],hot_spot['gene'],hot_spot['referenceAminoAcid'],hot_spot['variantAminoAcid'],
                                                   hot_spot['begin'],hot_spot['end'],str(hot_spot['position']),graph_id))

def create_hot_spot_occurrences_table(my_cursor):
    table_name = 'hot_spot_occurrences'
    if not does_table_exist(my_cursor, table_name):
        mySql_Create_Table_Query = 'CREATE TABLE hot_spot_occurrences ( ' \
                                   'id MEDIUMINT NOT NULL AUTO_INCREMENT, ' \
                                   'disease varchar(100) NOT NULL, ' \
                                   'oncoTreeCode varchar(20) NOT NULL, ' \
                                   'percentOccurrence varchar(10) NOT NULL, ' \
                                   'perThousandOccurrence MEDIUMINT NOT NULL, ' \
                                   'occurrences MEDIUMINT NOT NULL, ' \
                                   'totalSamples MEDIUMINT NOT NULL, ' \
                                   'hot_spot_id varchar(100), ' \
                                  'PRIMARY KEY (id),' \
                                   'CONSTRAINT hs_occurrences_fk_hotspot_id FOREIGN KEY (hot_spot_id) REFERENCES hot_spot (graph_id) ' \
                                   ')'
        result = my_cursor.execute(mySql_Create_Table_Query)
        print(f'{table_name} Table created successfully')

def insert_hotspot_occurrence(my_cursor,hot_spot_occurrence,hot_spot_id):
    mySql_insert_query = "INSERT INTO hot_spot_occurrences (disease,oncoTreeCode,percentOccurrence,perThousandOccurrence,occurrences, totalSamples,hot_spot_id) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(hot_spot_occurrence['disease'],hot_spot_occurrence['oncoTreeCode'],hot_spot_occurrence['percentOccurrence'],
                                                   str(hot_spot_occurrence['perThousand']),str(hot_spot_occurrence['occurences']),str(hot_spot_occurrence['totalSamples']),hot_spot_id))


def handle_occurrences(occurrences, onco_dict):
    occurrences_list = []
    occurrence_array = occurrences.split('|')
    for item in occurrence_array:
        vals = item.split(':')
        disease = vals[0]
        total = int(vals[1])
        has_variant = int(vals[2])
        ratio = 100.0 * (has_variant / total)
        onco_tree_occurrence = {'percentOccurrence': '%.1f%%' % ratio,
                                'perThousand': round(10.0 * ratio),
                                'occurences': has_variant,
                                'totalSamples': total}
        if disease in onco_dict:
            onco_tree_occurrence['disease'] = onco_dict[disease]['name']
            onco_tree_occurrence['oncoTreeCode'] = onco_dict[disease]['code']
        else:
            onco_tree_occurrence['disease'] = disease
            onco_tree_occurrence['oncoTreeCode'] = disease
        occurrences_list.append(onco_tree_occurrence)
    return occurrences_list


def get_oncotree_dict():
    onco_dict = {}
    unknown = {'code':'unk', 'name':'Unknown'}
    onco_dict['unk'] = unknown
    f = open('onctoree.json', "r")
    data = json.loads(f.read())
    f.close()
    for item in data:
        onco_dict[item['code'].lower()] = item
        for h in item['history']:
            onco_dict[h.lower()] = item
        for p in item['precursors']:
            onco_dict[p.lower()] = item
    return onco_dict

def main():
    onco_dict = get_oncotree_dict()
    hot_spots = read_snv_hotspot(onco_dict)
    hot_spots.extend(read_indel_hotspot(onco_dict))

    my_db = None
    my_cursor = None
    try:
        my_db = get_local_db_connection()
        my_cursor = my_db.cursor(buffered=True)
        maybe_create_and_select_database(my_cursor, 'OmniSeqKnowledgebase')
        drop_table_if_exists(my_cursor, 'hot_spot_occurrences')
        drop_table_if_exists(my_cursor, 'hot_spot')
        create_hot_spot_table(my_cursor)
        create_hot_spot_occurrences_table(my_cursor)
        for hot_spot in hot_spots:
            graph_id = 'hot_spot_' + hot_spot['name'].replace(' ','_').replace('-','_').replace('*','')
            insert_hotspot(my_cursor, hot_spot, graph_id)
            for occurrence in hot_spot['occurrences']:
                insert_hotspot_occurrence(my_cursor,occurrence,graph_id)
            my_db.commit()
    except mysql.connector.Error as error:
        print("Failed in MySQL: {}".format(error))
    finally:
        if my_db.is_connected():
            my_cursor.close()


if __name__ == "__main__":
    main()

