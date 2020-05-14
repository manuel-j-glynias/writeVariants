import datetime

import mysql.connector
from sql_utils import does_table_exist, get_local_db_connection, drop_table_if_exists, maybe_create_and_select_database
import xml.etree.ElementTree as ET


def get_cDot(variantName):
    if (len(variantName) > 0 and ':' in variantName):
        vn = variantName.split(':')[1]
        if (' ' in vn):
            variantName = vn.split()[0]
        else:
            variantName = vn
    return variantName


def getSignificanceTuple(sigDict):
    maxVal = 0
    maxName = ''
    explain = ''
    for significance in sigDict:
        if (len(explain) > 0):
            explain += "/"
        explain += significance + "(" + str(sigDict[significance]) + ")"
        if (sigDict[significance] > maxVal):
            maxVal = sigDict[significance]
            maxName = significance
    return maxName, explain


# def getCount(sigDict, key):
#     count = 0
#     if key in sigDict:
#         count = sigDict[key]
#     return count
#
#
# def getAllCounts(sigDict):
#     pathogenic = getCount(sigDict, 'pathogenic') + getCount(sigDict, 'likely pathogenic') + getCount(sigDict,
#                                                                                                      'drug response')
#     benign = getCount(sigDict, 'benign') + getCount(sigDict, 'likely benign') + getCount(sigDict,
#                                                                                          'no known pathogenicity')
#     uncertain = getCount(sigDict, 'uncertain significance')
#     return pathogenic, benign, uncertain

def convert_cdot_to_position(cdot):
    pos = None
    pos_string = ''
    for ch in cdot[2:]:
        if ch.isdigit():
            pos_string = pos_string + ch
        else:
            break
    if len(pos_string) > 0:
        pos = int(pos_string)
    return pos


def getOneVariant(variationArchive):
    clinvar = {
        'variantID': '',
        'gene': '',
        'cDot': '',
        'pDot': '',
        'cdot_pos': 0,
        'pdot_pos': 0,
        'significance': '',
        'signficanceExplanation': '',
    }
    variantName = ''
    sigs = {}
    for simpleAllele in variationArchive.iter('SimpleAllele'):
        if 'VariationID' in simpleAllele.attrib:
            clinvar['variantID'] = simpleAllele.attrib['VariationID']

    for gene in variationArchive.iter('Gene'):
        clinvar['gene'] = gene.attrib['Symbol']
    for name in variationArchive.iter('Name'):
        if (len(variantName) == 0):
            variantName = name.text
    for proteinChange in variationArchive.iter('ProteinChange'):
        if len(clinvar['pDot'])==0:
            clinvar['pDot'] = proteinChange.text
    for clinicalAssertion in variationArchive.iter('ClinicalAssertion'):
        for child in clinicalAssertion:
            if (child.tag == 'Interpretation'):
                for gc in child:
                    if (gc.tag == 'Description'):
                        significance = gc.text.lower()
                        sigs[significance] = sigs.get(significance, 0) + 1
    clinvar['cDot'] = get_cDot(variantName)
    pos = convert_cdot_to_position(clinvar['cDot'])
    if pos is not None:
        clinvar['cdot_pos'] = pos
        clinvar['pdot_pos'] = int((int(pos) + 2) / 3)

    clinvar['significance'], clinvar['signficanceExplanation'] = getSignificanceTuple(sigs)

    return clinvar


def create_clinvar_table(my_cursor):
    table_name = 'clinvar'
    if not does_table_exist(my_cursor, table_name):
        mySql_Create_Table_Query = 'CREATE TABLE clinvar ( ' \
                                   'id MEDIUMINT NOT NULL AUTO_INCREMENT PRIMARY KEY , ' \
                                   'variantID varchar(100), ' \
                                   'gene varchar(100), ' \
                                    'pDot varchar(100), ' \
                                   'cDot varchar(100), ' \
                                   'significance varchar(100), ' \
                                   'signficanceExplanation varchar(200), ' \
                                   'cdot_pos BIGINT, ' \
                                   'pdot_pos BIGINT, ' \
                                    'graph_id varchar(100) ' \
                                  ')'
        print(mySql_Create_Table_Query)
        result = my_cursor.execute(mySql_Create_Table_Query)
        print(f'{table_name} Table created successfully')

def insert_clinvar(my_cursor,clinvar,graph_id):
    mySql_insert_query = "INSERT INTO clinvar (variantID,gene,pDot,cDot,significance,signficanceExplanation,cdot_pos,pdot_pos,graph_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(clinvar['variantID'],clinvar['gene'],clinvar['pDot'],clinvar['cDot'],
                                                   clinvar['significance'],clinvar['signficanceExplanation'],str(clinvar['cdot_pos']),str(clinvar['pdot_pos']),graph_id))


def parse_xml_file(my_db,my_cursor,path):
    counter = 0
    id_dict = {}
    for event, elem in ET.iterparse(path):
        if event == 'end':
            if elem.tag == 'VariationArchive':
                clinvar = getOneVariant(elem)
                id = clinvar['variantID']
                if id in id_dict:
                    now = datetime.datetime.now()
                    id = id +  now.strftime("%Y%m%d%H%M%S%f")
                id_dict[id] = id
                graphql = 'clinvar_variant_' + id
                # print(clinvar)
                if not 'HAPLOTYPE' in clinvar['cDot'] and len(clinvar['cDot'])<100:
                    insert_clinvar(my_cursor,clinvar,graphql)
                counter += 1
                if (counter % 1000 == 0):
                    print(counter)
                    my_db.commit()
                elem.clear()  # discard the element

    my_db.commit()

def main():
    my_db = None
    my_cursor = None
    filename = 'data/ClinVarVariationRelease_2020-05.xml'
    try:
        my_db = get_local_db_connection()
        my_cursor = my_db.cursor(buffered=True)
        maybe_create_and_select_database(my_cursor, 'OmniSeqKnowledgebase')
        drop_table_if_exists(my_cursor, 'clinvar')
        create_clinvar_table(my_cursor)

        parse_xml_file(my_db,my_cursor,filename)

    except mysql.connector.Error as error:
        print("Failed in MySQL: {}".format(error))
    finally:
        if my_db.is_connected():
            my_cursor.close()


if __name__ == "__main__":
    main()

