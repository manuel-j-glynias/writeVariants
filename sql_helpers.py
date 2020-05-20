from graphql_utils import get_reference_from_pmid_by_metapub, fix_author_id, ref_name_from_authors_pmid_and_year, \
    get_authors_names


def get_one_author(id, my_cursor):
    a_dict = None
    query = f'SELECT * FROM OmniSeqKnowledgebase.authors where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row!= None:
        a_dict = get_author_dict_from_row(row)
    return a_dict


def get_author_dict_from_row(row):
    a_dict = {'id': row[2], 'firstInitial': row[1], 'surname': row[0]}
    return a_dict


def get_one_journal(id, my_cursor):
    j_dict = None
    query = f'SELECT * FROM OmniSeqKnowledgebase.journals where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row!= None:
        j_dict = {'id': row[1], 'name': row[0]}
    return j_dict


def get_one_user(id, my_cursor):
    u_dict = None
    query = f'SELECT * FROM OmniSeqKnowledgebase.users where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    # name, password, isAdmin, graph_id
    if row!= None:
        u_dict = user_dict_from_row(row)
    return u_dict


def user_dict_from_row(row):
    admin = row[2] == 'TRUE'
    u_dict = {'id': row[3], 'name': row[0], 'password': row[1], 'isAdmin': admin}
    return u_dict


def es_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor):
    # 0      1           2          3        4         5     6        7        8
    # field, statement, edit_date, deleted, graph_id, name, password, isAdmin, graph_id
    admin = row[7] == 'TRUE'
    u_dict = {'id': row[8], 'name': row[5], 'password': row[6], 'isAdmin': admin}
    references = []
    if shouldReturn_References:
        q1 = f'SELECT r.PMID, r.DOI, r.title, r.journal_graph_id, r.volume, r.first_page, r.last_page, r.publication_Year, r.short_reference, r.abstract, r.graph_id, x.ref_id FROM OmniSeqKnowledgebase.es_ref x  INNER JOIN OmniSeqKnowledgebase.refs r on r.graph_id=x.ref_id where es_id="{row[4]}";'
        my_cursor.execute(q1)
        for r1 in my_cursor.fetchall():
            references.append(create_dict_from_ref_row(r1, shouldReturn_Authors, my_cursor))
        q2 = f'SELECT r.accessed_date, r.web_address, r.short_reference, r.graph_id, x.internet_ref_id FROM OmniSeqKnowledgebase.es_internet_refs x INNER JOIN OmniSeqKnowledgebase.internet_refs r on r.graph_id=x.internet_ref_id where es_id="{row[4]}";'
        my_cursor.execute(q2)
        for r2 in my_cursor.fetchall():
            references.append(create_dict_from_internet_ref_row(r2, my_cursor))
    es_dict = { 'id': row[4], 'field': row[0],'statement': row[1],'editor': u_dict,'editDate': row[2],'deleted': row[3],'references':references}
    return es_dict


def get_one_es(id, shouldReturn_References, shouldReturn_Authors, my_cursor):
    es_dict = {}
    query = f'SELECT es.field, es.statement, es.edit_date,  es.deleted, es.graph_id, u.name, u.password, u.isAdmin, u.graph_id FROM OmniSeqKnowledgebase.editable_statements es INNER JOIN OmniSeqKnowledgebase.users u ON es.editor_id = u.graph_id where es.graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    # name, password, isAdmin, graph_id
    if row!= None:
        es_dict = es_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor)
    return es_dict


def jax_gene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor):
    es_dict = get_one_es(row[5], shouldReturn_References, shouldReturn_Authors, my_cursor)
    synonyms = []
    synonym_query = f'SELECT name FROM OmniSeqKnowledgebase.jax_synonyms where jax_gene_id="{row[6]}";'
    my_cursor.execute(synonym_query)
    for s_row in my_cursor.fetchall():
        synonyms.append(s_row[0])
    canonicalTranscript = []
    canonicalTranscript.append(str(row[1]))
    # 0     1                     2          3          4     5               6
    # name, canonicalTranscript, chromosome, entrezId, jaxId, description_Id, graph_id
    jax_dict = { 'id': row[6], 'name': row[0],'description': es_dict,'entrezId': row[3],'jaxId': row[4],'chromosome': row[2],'synonyms':synonyms, 'canonicalTranscript': canonicalTranscript}

    return jax_dict


def get_one_jax_gene(id, shouldReturn_References, shouldReturn_Authors, my_cursor):
    jax_dict = {}
    query = f'SELECT * FROM OmniSeqKnowledgebase.jax_gene where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    # name, password, isAdmin, graph_id
    if row!= None:
        jax_dict = jax_gene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor)
    return jax_dict


def create_dict_from_ref_row(row, shouldReturn_Authors: bool, my_cursor):
    # 0     1      2      3                4          5           6                 7               8          9       10
    # PMID, DOI, title, journal_graph_id, volume, first_page, last_page, publication_Year, short_reference, abstract, graph_id
    j_dict = get_one_journal(row[3], my_cursor)
    authors = []
    if shouldReturn_Authors:
        author_query = f'SELECT author_id FROM OmniSeqKnowledgebase.author_ref where ref_id="{row[10]}";'
        my_cursor.execute(author_query)
        for a_row in my_cursor.fetchall():
            author_id = a_row[0]
            a_dict = get_one_author(author_id, my_cursor)
            authors.append(a_dict)
    statementsReferenced = []
    es_query = f'SELECT es_id FROM OmniSeqKnowledgebase.es_ref where ref_id="{row[10]}";'
    my_cursor.execute(es_query)
    for es_row in my_cursor.fetchall():
        statementsReferenced.append(get_one_es(es_row[0], False, False, my_cursor))
    d =  {'id': row[10], 'PMID': row[0], 'DOI': row[1], 'title': row[2], 'journal': j_dict, 'volume': row[4], 'firstPage': row[5],
                       'lastPage': row[6], 'publicationYear': row[7], 'shortReference': row[8], 'abstract': row[9],
          'authors':authors, 'statementsReferenced': statementsReferenced,  'type':'LiteratureReference'}
    return d


def create_dict_from_internet_ref_row(row, my_cursor):
    # 0               1            2               3                4
    # accessed_date, web_address, short_reference, graph_id
    statementsReferenced = []
    es_query = f'SELECT es_id FROM OmniSeqKnowledgebase.es_internet_refs where internet_ref_id="{row[3]}";'
    my_cursor.execute(es_query)
    for es_row in my_cursor.fetchall():
        statementsReferenced.append(get_one_es(es_row[0], False, False, my_cursor))
    d =  {'id': row[3], 'shortReference': row[2], 'webAddress': row[1], 'accessedDate': row[0],
          'statementsReferenced': statementsReferenced, 'type':'InternetReference'}
    return d


def mygeneinfo_gene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, should_return_uniprot, my_cursor):
    es_dict = get_one_es(row[6], shouldReturn_References, shouldReturn_Authors, my_cursor)
    if should_return_uniprot:
        uniprotEntry = get_one_uniprot_by_gene_id(row[7], shouldReturn_References, shouldReturn_Authors, False,
                                                  my_cursor)
    else:
        uniprotEntry = {'name':'-'}
    synonyms = []
    # 0     1           2          3          4     5               6              7
    # name, chromosome, strand, start_pos, end_pos, entrezId, description_Id, graph_id
    strand = 'Forward'
    if row[2]=='REVERSE':
        strand = 'Reverse'
    gene_dict = { 'id': row[7], 'name': row[0],'description': es_dict,'chromosome': row[1],'strand': strand, 'start':int(row[3]),'end':int(row[4]),'synonyms':synonyms, 'entrezId': row[5], 'uniprotEntry':uniprotEntry}

    return gene_dict


def get_one_mygeneinfo_gene(id, shouldReturn_References, shouldReturn_Authors, should_return_uniprot, my_cursor):
    gene_dict = {}
    query = f'SELECT * FROM OmniSeqKnowledgebase.mygene_info_gene where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    # name, password, isAdmin, graph_id
    if row!= None:
        gene_dict = mygeneinfo_gene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors,
                                                  should_return_uniprot, my_cursor)
    return gene_dict


def uniprot_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, should_return_gene, my_cursor):
    es_dict = get_one_es(row[3], shouldReturn_References, shouldReturn_Authors, my_cursor)
    if should_return_gene:
        gene = get_one_mygeneinfo_gene(row[4], shouldReturn_References, shouldReturn_Authors, False, my_cursor)
    else:
        gene = {'name':'-'}
    # 0     1                2            3           4         5
    # name, accessionNumber, uniprot_id, function_Id, gene_Id, graph_id
    uniprot = { 'id': row[5], 'name': row[0],'function': es_dict, 'uniprotID': row[2], 'accessionNumber': row[1], 'gene':gene}

    return uniprot


def get_one_uniprot(id, shouldReturn_References, shouldReturn_Authors, should_return_gene, my_cursor):
    uniprot = {}
    query = f'SELECT * FROM OmniSeqKnowledgebase.uniprot_entry where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row!= None:
        uniprot = uniprot_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, should_return_gene,
                                        my_cursor)
    return uniprot


def get_one_uniprot_by_gene_id(gene_id, shouldReturn_References, shouldReturn_Authors, should_return_gene, my_cursor):
    uniprot = {}
    query = f'SELECT * FROM OmniSeqKnowledgebase.uniprot_entry where gene_Id="{gene_id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row!= None:
        uniprot = uniprot_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, should_return_gene,
                                        my_cursor)
    return uniprot


def omnigene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor):
    geneDescription = get_one_es(row[2], shouldReturn_References, shouldReturn_Authors, my_cursor)
    oncogenicCategory = get_one_es(row[3], shouldReturn_References, shouldReturn_Authors, my_cursor)
    synonymsString = get_one_es(row[4], shouldReturn_References, shouldReturn_Authors, my_cursor)

    gene = get_one_mygeneinfo_gene(row[5], shouldReturn_References, shouldReturn_Authors, False, my_cursor)
    uniprotEntry = get_one_uniprot(row[7], shouldReturn_References, shouldReturn_Authors, False, my_cursor)
    jax_gene = get_one_jax_gene(row[6], shouldReturn_References, shouldReturn_Authors, my_cursor)

    # 0     1          2                    3                     4                 5                    6                7                 8
    # name, panelName, geneDescription_id, oncogenicCategory_Id, synonymsString_Id, myGeneInfo_gene_Id, jaxGene_gene_Id, uniprot_entry_Id, graph_id
    omnigene = { 'id': row[8], 'name': row[0], 'panelName': row[1], 'geneDescription':geneDescription, 'oncogenicCategory':oncogenicCategory, 'synonymsString':synonymsString,
                 'myGeneInfoGene':gene, 'uniprotEntry':uniprotEntry, 'jaxGene': jax_gene}

    return omnigene


def get_one_omnigene(id, shouldReturn_References, shouldReturn_Authors, my_cursor):
    omnigene = {}
    query = f'SELECT * FROM OmniSeqKnowledgebase.omnigene where graph_id="{id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    # name, password, isAdmin, graph_id
    if row!= None:
        omnigene = omnigene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor)
    return omnigene


def get_one_omnigene_by_name(name, shouldReturn_References, shouldReturn_Authors, my_cursor):
    omnigene = {}
    query = f'SELECT * FROM OmniSeqKnowledgebase.omnigene where name="{name}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    # name, password, isAdmin, graph_id
    if row!= None:
        omnigene = omnigene_dict_from_row(row, shouldReturn_References, shouldReturn_Authors, my_cursor)
    return omnigene


def get_where_clause(filter:dict):
    where = ''
    fragments = None
    conj = ''
    if 'OR' in filter:
        conj = ' or '
        fragments = filter['OR']
    elif 'AND' in filter:
        conj = ' and '
        fragments = filter['AND']
    if fragments != None:
        for frag in fragments:
            if where != '':
                where += conj
            where += get_where_fragment(frag)
    else:
        where = get_where_fragment(filter)

    return 'where ' + where


def get_where_fragment(filter_dict):
    where = ''
    if 'name_starts_with' in filter_dict:
        starts = filter_dict['name_starts_with']
        where += f'name like "{starts}%"'
    elif 'panelName_starts_with' in filter_dict:
        starts = filter_dict['panelName_starts_with']
        where += f'panelName like "{starts}%"'
    return where


def is_author_db(my_cursor,author_id):
    query = f'SELECT * FROM OmniSeqKnowledgebase.authors where graph_id="{author_id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    return row != None


def insert_author(my_cursor,surname,first_initial,graph_id):
    mySql_insert_query = "INSERT IGNORE INTO authors (surname, first_initial, graph_id) VALUES (%s, %s, %s)"
    result = my_cursor.execute(mySql_insert_query, (surname,first_initial,graph_id))


def insert_author_ref(my_cursor,author_id,ref_id):
    mySql_insert_query = f"INSERT INTO author_ref (author_id,ref_id) " \
                         f"VALUES ('{author_id}', '{ref_id}') "
    result = my_cursor.execute(mySql_insert_query)


def insert_journal(my_cursor,name,graph_id):
    mySql_insert_query = "INSERT INTO journals (name, graph_id) VALUES (%s, %s)"
    result = my_cursor.execute(mySql_insert_query,(name,graph_id))


def create_journal_if_not_exists(my_cursor,journal_id, journal):
    query = f'SELECT * FROM OmniSeqKnowledgebase.journals where graph_id="{journal_id}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row == None:
        insert_journal(my_cursor,journal,journal_id)


def insert_reference(my_cursor,PMID,DOI,title,journal_graph_id,volume,first_page,last_page,publication_Year,short_reference,abstract,graph_id):
    mySql_insert_query = "INSERT INTO refs (PMID,DOI,title,journal_graph_id,volume,first_page,last_page,publication_Year,short_reference,abstract,graph_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(PMID,DOI,title,journal_graph_id,volume,first_page,last_page,publication_Year,short_reference,abstract,graph_id))


def preflight_ref(pmid:str,my_cursor):
    graph_id = None
    query = f'SELECT * FROM OmniSeqKnowledgebase.refs where PMID="{pmid}";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    if row==None:
        reference = get_reference_from_pmid_by_metapub(pmid)
        if reference != None:
            graph_id = 'ref_' + str(pmid)
            journal = reference['journal']
            journal_id = 'journal_' + fix_author_id(journal)
            create_journal_if_not_exists(my_cursor,journal_id,journal)
            short_ref = ref_name_from_authors_pmid_and_year(reference['authors'], reference['pmid'], reference['year'])
            insert_reference(my_cursor,reference['pmid'],reference['doi'],reference['title'],journal_id,reference['volume'],reference['first_page'],
                             reference['last_page'],reference['year'],short_ref,reference['abstract'],graph_id)
            for author in reference['authors']:
                first, surname = get_authors_names(author)
                author_id = fix_author_id('author_' + surname + '_' + first)
                if not is_author_db(my_cursor,author_id):
                    # print(author_id)
                    insert_author(my_cursor,surname,first,author_id)
                insert_author_ref(my_cursor,author_id,graph_id)
    else:
        graph_id = row[10]
    return graph_id


def insert_editable_statement(my_cursor,field, statement, edit_date,editor_id,deleted,graph_id):
    mySql_insert_query = "INSERT INTO editable_statements (field,statement,edit_date,editor_id,deleted,graph_id) VALUES (%s,%s,%s,%s,%s,%s)"
    result = my_cursor.execute(mySql_insert_query,(field, statement, edit_date,editor_id,deleted,graph_id))


def insert_es_ref(my_cursor,es_id,ref_id):

    mySql_insert_query = f"INSERT INTO es_ref (es_id,ref_id) " \
                         f"VALUES ('{es_id}', '{ref_id}') "
    result = my_cursor.execute(mySql_insert_query)


def get_loader_user_id(my_cursor):
    query = 'SELECT graph_id FROM OmniSeqKnowledgebase.users where name="loader";'
    my_cursor.execute(query)
    row = my_cursor.fetchone()
    return row[0]