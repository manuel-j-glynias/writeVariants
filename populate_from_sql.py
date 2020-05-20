from sql_utils import get_cloud_db_connection, maybe_create_and_select_database, get_local_db_connection
from graphql_utils import erase_neo4j, create_author_mutation, create_journal_mutation, send_mutation, \
    create_AddLiteratureReferenceJournal_mutation, create_AddLiteratureReferenceAuthors_mutation


def write_authors(my_cursor, server_write):
    print('write_authors')
    query = 'SELECT * FROM OmniSeqKnowledgebase.authors;'
    my_cursor.execute(query)
    authors = my_cursor.fetchall()
    m = ''
    counter = 0
    for author in authors:
        s = create_author_mutation(author[2], author[0], author[1])
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    send_mutation(m, server_write)


def write_journals(my_cursor, server_write):
    print('write_journals')
    query = 'SELECT * FROM OmniSeqKnowledgebase.journals;'
    my_cursor.execute(query)
    journals = my_cursor.fetchall()
    m = ''
    for journal in journals:
        # print(journal)
        s = create_journal_mutation(journal[0], journal[1])
        m += s
    send_mutation(m, server_write)

# PMID, DOI, title, journal_graph_id, volume, first_page, last_page, publication_Year, short_reference, abstract, graph_id
# 0     1    2       3                 4      5            6         7                  8               9         10
def create_reference_mutation(ref):
    s = f'''{ref[10]}: createLiteratureReference(id: \\"{ref[10]}\\", abstract: \\"{ref[9]}\\", shortReference: \\"{ref[8]}\\", title: \\"{ref[2]}\\", volume: \\"{ref[4]}\\", firstPage: \\"{ref[5]}\\", lastPage: \\"{ref[6]}\\", publicationYear: \\"{ref[7]}\\", DOI: \\"{ref[1]}\\", PMID: \\"{ref[0]}\\"),'''
    return s


def write_references(my_cursor, server_write):
    print('write_references')
    query = 'SELECT * FROM OmniSeqKnowledgebase.refs;'
    my_cursor.execute(query)
    refs = my_cursor.fetchall()
    m = ''
    counter = 0
    for ref in refs:
        # print(ref)
        s = create_reference_mutation(ref)
        s += create_AddLiteratureReferenceJournal_mutation(ref[10],ref[3])
        au_query = f'SELECT author_id FROM OmniSeqKnowledgebase.author_ref where ref_id="{ref[10]}";'
        my_cursor.execute(au_query)
        authors = []
        for row in my_cursor.fetchall():
            authors.append(row[0])
        s += create_AddLiteratureReferenceAuthors_mutation(ref[10],authors)
        # print(s)
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    send_mutation(m, server_write)


def write_internet_references(my_cursor, server_write):
    print('write_internet_references')
    query = 'SELECT * FROM OmniSeqKnowledgebase.internet_refs;'
    my_cursor.execute(query)
    irefs = my_cursor.fetchall()
    m = ''
    for iref in irefs:
        # print(iref)
        # accessed_date, web_address, short_reference, graph_id
        s = f'{iref[3]}: createInternetReference(accessedDate:\\"{iref[0]}\\", id:\\"{iref[3]}\\", shortReference: \\"{iref[2]}\\", webAddress:\\"{iref[1]}\\" ),'
        m += s
    send_mutation(m, server_write)


def write_users(my_cursor, server_write):
    print('write_users')
    query = 'SELECT * FROM OmniSeqKnowledgebase.users;'
    my_cursor.execute(query)
    users = my_cursor.fetchall()
    m = ''
    for user in users:
        # print(user)
        # name, password, isAdmin, graph_id
        s = f'{user[3]}: createUser(id:\\"{user[3]}\\", isAdmin:{return_graphql_boolean_from_sql(user[2])}, name:\\"{user[0]}\\", password:\\"{user[1]}\\"),'
        m += s
    send_mutation(m, server_write)


def return_graphql_boolean_from_sql(bool_as_sql_string:str):
    return bool_as_sql_string.lower()


def write_editable_statements(my_cursor, server_write):
    print('write_editable_statements')
    query = 'SELECT * FROM OmniSeqKnowledgebase.editable_statements;'
    my_cursor.execute(query)
    ess = my_cursor.fetchall()
    m = ''
    counter = 0
    for es in ess:
        # field, statement, edit_date, editor_id, deleted, graph_id
        statement = str(es[1])
        statement = statement.replace('\n',' ')
        s = f'{es[5]} : createEditableStatement(deleted: {return_graphql_boolean_from_sql(es[4])}, editDate: \\"{es[2]}\\", field: \\"{es[0]}\\", id: \\"{es[5]}\\",statement: \\"{statement}\\"),'

        ede_id: str = 'ese_' + es[2].replace('-', '')
        s += f'{ede_id}: addEditableStatementEditor(editor:[\\"{es[3]}\\"], id:\\"{es[5]}\\" ),'

        refs = '['
        ref_query = f'SELECT * FROM OmniSeqKnowledgebase.es_ref where es_id="{es[5]}";'
        my_cursor.execute(ref_query)
        # id, es_id, ref_id
        for row in my_cursor.fetchall():
            refs += '\\"' + str(row[2]) + '\\",'

        iref_query = f'SELECT * FROM OmniSeqKnowledgebase.es_internet_refs where es_id="{es[5]}";'
        my_cursor.execute(iref_query)
        # id, es_id, ref_id
        for row in my_cursor.fetchall():
            refs += '\\"' + str(row[2]) + '\\",'

        refs += ']'
        ref_id = 'ref_' + es[5]
        s += f'{ref_id}: addEditableStatementReferences(id:\\"{es[5]}\\", references:{refs}),'
        # print(s)
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    send_mutation(m, server_write)

def write_jax_genes(my_cursor, server_write):
    print('write_jax_genes')
    query = 'SELECT * FROM OmniSeqKnowledgebase.jax_gene;'
    my_cursor.execute(query)
    j_genes = my_cursor.fetchall()
    m = ''
    counter = 0
    for gene in j_genes:
        syn_query = f'SELECT * FROM OmniSeqKnowledgebase.jax_synonyms where jax_gene_id="{gene[6]}";'
        my_cursor.execute(syn_query)
        synonyms = '['
        for row in my_cursor.fetchall():
            synonyms += '\\"' + str(row[1]) + '\\",'
        synonyms += ']'
        # name, canonicalTranscript, chromosome, entrezId, jaxId, description_Id, graph_id
        s = f'''{gene[6]} : createJaxGene(canonicalTranscript: \\"{gene[1]}\\", chromosome: \\"{gene[2]}\\",entrezId: \\"{gene[3]}\\", id: \\"{gene[6]}\\", jaxId: \\"{gene[4]}\\", name: \\"{gene[0]}\\", synonyms: {synonyms}),'''
        jvd_id = 'jvd_' + str(counter)
        s += f'{jvd_id}: addJaxGeneDescription(description:[\\"{gene[5]}\\"], id:\\"{gene[6]}\\"),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_mygene_genes(my_cursor, server_write):
    print('write_mygene_genes')
    query = 'SELECT * FROM OmniSeqKnowledgebase.mygene_info_gene;'
    my_cursor.execute(query)
    my_genes = my_cursor.fetchall()
    m = ''
    counter = 0
    for gene in my_genes:
        # name, chromosome, strand, start_pos, end_pos, entrezId, description_Id, graph_id
        synonyms = '[]'
        strand = 'Forward'
        if gene[2]=='REVERSE' or gene[2]=='Reverse':
            strand = 'Reverse'
        s = f'{gene[7]}: createMyGeneInfoGene(chromosome: \\"{gene[1]}\\", end: {gene[4]}, entrezId: \\"{gene[5]}\\", id: \\"{gene[7]}\\", name: \\"{gene[0]}\\" start: {gene[3]},  strand:{strand},synonyms: {synonyms}),'
        jvd_id = 'jvd_' + str(counter)
        s += f'{jvd_id}: addMyGeneInfoGeneDescription(description:[\\"{gene[6]}\\"], id:\\"{gene[7]}\\"),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_uniprot(my_cursor, server_write):
    print('write_uniprot')
    query = 'SELECT * FROM OmniSeqKnowledgebase.uniprot_entry;'
    my_cursor.execute(query)
    uniprot = my_cursor.fetchall()
    m = ''
    counter = 0
    for prot in uniprot:
        # 0     1                 2            3           4        5
        # name, accessionNumber, uniprot_id, function_Id, gene_Id, graph_id
        s = f'{prot[5]}: createUniprotEntry(accessionNumber: \\"{prot[1]}\\", id: \\"{prot[5]}\\", name: \\"{prot[0]}\\",  uniprotID:\\"{prot[2]}\\"),'
        jvd_id = 'upg_' + str(counter)
        s += f'{jvd_id}:addUniprotEntryGene(gene:[\\"{prot[4]}\\"], id:\\"{prot[5]}\\" ),'
        jvd_id = 'upf_' + str(counter)
        s += f'{jvd_id}:addUniprotEntryFunction(function:[\\"{prot[3]}\\"], id:\\"{prot[5]}\\" ),'
        m += s
        counter += 1

        # send_mutation(m, server_write)
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_omnigene(my_cursor, server_write):
    print('write_omnigene')
    query = 'SELECT * FROM OmniSeqKnowledgebase.omnigene;'
    my_cursor.execute(query)
    genes = my_cursor.fetchall()
    m = ''
    counter = 0
    for gene in genes:
        #          0     1          2                   3                    4                   5                  6                7                  8
        #         name, panelName, geneDescription_id, oncogenicCategory_Id, synonymsString_Id, myGeneInfo_gene_Id, jaxGene_gene_Id, uniprot_entry_Id, graph_id
        s = f'{gene[8]}: createOmniGene(id: \\"{gene[8]}\\", name: \\"{gene[0]}\\", panelName:\\"{gene[1]}\\" ),'
        jvd_id = 'omni_des_' + str(counter)
        s += f'{jvd_id}:addOmniGeneGeneDescription(geneDescription:[\\"{gene[2]}\\"], id:\\"{gene[8]}\\" ),'
        jvd_id = 'omni_cat_' + str(counter)
        s += f'{jvd_id}:addOmniGeneOncogenicCategory(id:\\"{gene[8]}\\", oncogenicCategory:[\\"{gene[3]}\\"] ),'
        jvd_id = 'omni_syn_' + str(counter)
        s += f'{jvd_id}:addOmniGeneSynonymsString(id:\\"{gene[8]}\\", synonymsString:[\\"{gene[4]}\\"] ),'
        if gene[6] != None:
            jvd_id = 'omni_jaxg_' + str(counter)
            s += f'{jvd_id}:addOmniGeneJaxGene(id:\\"{gene[8]}\\", jaxGene:[\\"{gene[6]}\\"] ),'
        if gene[5] != None:
            jvd_id = 'omni_myg_' + str(counter)
            s += f'{jvd_id}:addOmniGeneMyGeneInfoGene(id:\\"{gene[8]}\\", myGeneInfoGene:[\\"{gene[5]}\\"] ),'
        if gene[7] != None:
            jvd_id = 'omni_uni_' + str(counter)
            s += f'{jvd_id}:addOmniGeneUniprotEntry(id:\\"{gene[8]}\\", uniprotEntry:[\\"{gene[7]}\\"] ),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_jax_variants(my_cursor, server_write):
    print('write_jax_variants')
    query = 'SELECT * FROM OmniSeqKnowledgebase.jax_variant;'
    my_cursor.execute(query)
    variants = my_cursor.fetchall()
    m = ''
    counter = 0
    for jv in variants:
        s = f'{jv[10]}: createJaxVariant(cDot: \\"{jv[5]}\\", gDot: \\"{jv[6]}\\",id: \\"{jv[10]}\\",jaxId: \\"{jv[2]}\\",' \
            f'name: \\"{jv[0]}\\",pDot: \\"{jv[4]}\\",proteinEffect: \\"{jv[9]}\\",transcript: \\"{jv[7]}\\",variantType: \\"{jv[8]}\\", ),'
        jvd_id = 'jvd_' + jv[10] + '_' + jv[1]
        s += f'{jvd_id}: addJaxVariantDescription(description:[\\"{jv[1]}\\"], id:\\"{jv[10]}\\"),'
        m += s
        # addJaxVariantGene(gene: [ID!]!id: ID!): String
        jvg_id = 'jvg_' + jv[10] + '_' + jv[3]
        s += f'{jvg_id}: addJaxVariantGene(gene:[\\"{jv[3]}\\"], id:\\"{jv[10]}\\"),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_hot_spot_variants(my_cursor, server_write):
    print('write_hot_spot_variants')
    query = 'SELECT * FROM OmniSeqKnowledgebase.hot_spot;'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    m = ''
    counter = 0
    for row in rows:
        s = f'{row[7]}: createHotSpotVariant(begin: \\"{row[4]}\\", end: \\"{row[5]}\\", gene: \\"{row[1]}\\", id: \\"{row[7]}\\", name: \\"{row[0]}\\", position: {row[6]}, referenceAminoAcid: \\"{row[2]}\\", variantAminoAcid: \\"{row[3]}\\", ),'
        #
        # createOncoTreeOccurrence(disease: String!id: ID!occurences: Int! oncoTreeCode: String!percentOccurence: String!totalSamples: Int!): String
        occurrences = '['
        occurrences_query = f'SELECT * FROM OmniSeqKnowledgebase.hot_spot_occurrences where hot_spot_id="{row[7]}";'
        my_cursor.execute(occurrences_query)
        # id, es_id, ref_id
        for otc in my_cursor.fetchall():
            hso_id = 'hso_' + str(otc[0])
            s += f'{hso_id}: createOncoTreeOccurrence(disease: \\"{otc[1]}\\", id: \\"{otc[7]}\\", occurrences: {otc[5]}, oncoTreeCode: \\"{otc[2]}\\", percentOccurrence: \\"{otc[3]}\\", totalSamples: {otc[6]}, perThousandOccurrence: {otc[4]}, ),'
            occurrences += '\\"' + str(otc[7]) + '\\",'
        occurrences += ']'
        # addHotSpotVariantOccurrences(id: ID!occurrences: [ID!]!): String
        jvd_id = 'hsvo_' + row[7]
        s += f'{jvd_id}: addHotSpotVariantOccurrences(id:\\"{row[7]}\\", occurrences: {occurrences} ),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_clinvar_variants(my_cursor, server_write):
    print('write_clinvar_variants')
    query = 'SELECT * FROM OmniSeqKnowledgebase.clinvar;'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    m = ''
    counter = 0
    for row in rows:
        s = f'{row[8]}: createClinVarVariant(cDot: \\"{row[3]}\\", gene: \\"{row[1]}\\", id: \\"{row[8]}\\", pDot: \\"{row[2]}\\", signficanceExplanation: \\"{row[5]}\\", significance: \\"{row[4]}\\", variantID: \\"{row[0]}\\",),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)

def write_go_variants(my_cursor, server_write):
    print('write_go_variants')
    query = 'SELECT * FROM OmniSeqKnowledgebase.go_variant;'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    m = ''
    counter = 0
    for row in rows:
        s = f'{row[5]}: createGOVariant(gene: \\"{row[1]}\\", goID: \\"{row[2]}\\", id: \\"{row[5]}\\", mutationType: \\"{row[3]}\\", name: \\"{row[0]}\\", ),'
        m += s
        go_jax_id = 'gojaxv_' + row[5]
        s = f'{go_jax_id}: addGOVariantJaxVariant(id:\\"{row[5]}\\", jaxVariant: [\\"{row[4]}\\"]),'
        m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_snv(my_cursor, server_write):
    query = 'SELECT * FROM OmniSeqKnowledgebase.ocp_variant where variantType="SNV";'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    m = ''
    counter = 0
    for row in rows:
        indel_type = 'SNV'
        non_canonical_transcript = ''
        variant_type = 'SNV'
        protein_effect = get_protein_effect(row)
        s = f'{row[14]}: createVariantSNVIndel(cDot: \\"{row[4]}\\", gDot: \\"{row[5]}\\", id: \\"{row[14]}\\", indelType: {indel_type}, name: \\"{row[0]}\\", nonCanonicalTranscript: \\"{non_canonical_transcript}\\", pDot: \\"{row[3]}\\", proteinEffect: {protein_effect}, variantType: {variant_type}, ),'
        m += s
        m_id = 'snv_g_' + row[14]
        s = f'{m_id}: addVariantSNVIndelGene(id:\\"{row[14]}\\", gene: [\\"{row[1]}\\"]),'
        m += s
        m_id = 'snv_d_' + row[14]
        s = f'{m_id}: addVariantSNVIndelDescription(id:\\"{row[14]}\\", description: [\\"{row[2]}\\"]),'
        m += s
        jax_variant_id = row[10]
        # addVariantSNVIndelJaxVariant(id: ID!jaxVariant: [ID!]!): String
        if jax_variant_id != None:
            m_id = 'snv_jax_' + row[14]
            s = f'{m_id}: addVariantSNVIndelJaxVariant(id:\\"{row[14]}\\", jaxVariant: [\\"{jax_variant_id}\\"]),'
            m += s
        go_variant_id = row[11]
        # addVariantSNVIndelGoVariant(goVariant: [ID!]!id: ID!): String
        if go_variant_id != None:
            m_id = 'snv_go_' + row[14]
            s = f'{m_id}: addVariantSNVIndelGoVariant(id:\\"{row[14]}\\", goVariant: [\\"{go_variant_id}\\"]),'
            m += s
        clinVarVariant = row[12]
        # addVariantSNVIndelClinVarVariant(clinVarVariant: [ID!]!id: ID!): String
        if clinVarVariant != None:
            m_id = 'snv_cv_' + row[14]
            s = f'{m_id}: addVariantSNVIndelClinVarVariant(id:\\"{row[14]}\\", clinVarVariant: [\\"{clinVarVariant}\\"]),'
            m += s
        hot_spot_variant_id = row[13]
        # addVariantSNVIndelHotSpotVariant(hotSpotVariant: [ID!]!id: ID!): String
        if hot_spot_variant_id != None:
            m_id = 'snv_hot_spot_' + row[14]
            s = f'{m_id}: addVariantSNVIndelHotSpotVariant(id:\\"{row[14]}\\", hotSpotVariant: [\\"{hot_spot_variant_id}\\"]),'
            m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def get_protein_effect(row):
    protein_effect_dict = {
                            'gain of function':'GainOfFunction','gain of function - predicted':'GainOfFunctionPredicted',
                            'loss of function':'LossOfFunction','loss of function - predicted':'LossOfFunctionPredicted','no effect'  :'NoEffect','unkown':'Unknown'}

    _protein_effect = row[9]
    if _protein_effect in protein_effect_dict:
        protein_effect = protein_effect_dict[_protein_effect]
    else:
        protein_effect = 'Unknown'
    return protein_effect


def write_indels(my_cursor, server_write):
    indel_dict = { 'ins':'Insertion', 'del':'Deletion','dup':'Duplication'}
    query = 'SELECT * FROM OmniSeqKnowledgebase.ocp_variant where variantType="Indel";'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    m = ''
    counter = 0
    for row in rows:
        pre_indel_type = row[7]
        if pre_indel_type in indel_dict:
            indel_type = indel_dict[pre_indel_type]
        else:
            indel_type = ''
        non_canonical_transcript = ''
        variant_type = 'Indel'
        protein_effect = get_protein_effect(row)
        s = f'{row[14]}: createVariantSNVIndel(cDot: \\"{row[4]}\\", gDot: \\"{row[5]}\\", id: \\"{row[14]}\\", indelType: {indel_type}, name: \\"{row[0]}\\", nonCanonicalTranscript: \\"{non_canonical_transcript}\\", pDot: \\"{row[3]}\\", proteinEffect: {protein_effect}, variantType: {variant_type}, ),'
        m += s
        m_id = 'snv_g_' + row[14]
        s = f'{m_id}: addVariantSNVIndelGene(id:\\"{row[14]}\\", gene: [\\"{row[1]}\\"]),'
        m += s
        m_id = 'snv_d_' + row[14]
        s = f'{m_id}: addVariantSNVIndelDescription(id:\\"{row[14]}\\", description: [\\"{row[2]}\\"]),'
        m += s
        jax_variant_id = row[10]
        # addVariantSNVIndelJaxVariant(id: ID!jaxVariant: [ID!]!): String
        if jax_variant_id != None:
            m_id = 'snv_jax_' + row[14]
            s = f'{m_id}: addVariantSNVIndelJaxVariant(id:\\"{row[14]}\\", jaxVariant: [\\"{jax_variant_id}\\"]),'
            m += s
        go_variant_id = row[11]
        # addVariantSNVIndelGoVariant(goVariant: [ID!]!id: ID!): String
        if go_variant_id != None:
            m_id = 'snv_go_' + row[14]
            s = f'{m_id}: addVariantSNVIndelGoVariant(id:\\"{row[14]}\\", goVariant: [\\"{go_variant_id}\\"]),'
            m += s
        clinVarVariant = row[12]
        # addVariantSNVIndelClinVarVariant(clinVarVariant: [ID!]!id: ID!): String
        if clinVarVariant != None:
            m_id = 'snv_cv_' + row[14]
            s = f'{m_id}: addVariantSNVIndelClinVarVariant(id:\\"{row[14]}\\", clinVarVariant: [\\"{clinVarVariant}\\"]),'
            m += s
        hot_spot_variant_id = row[13]
        # addVariantSNVIndelHotSpotVariant(hotSpotVariant: [ID!]!id: ID!): String
        if hot_spot_variant_id != None:
            m_id = 'snv_hot_spot_' + row[14]
            s = f'{m_id}: addVariantSNVIndelHotSpotVariant(id:\\"{row[14]}\\", hotSpotVariant: [\\"{hot_spot_variant_id}\\"]),'
            m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_cnv(my_cursor, server_write):
    query = 'SELECT * FROM OmniSeqKnowledgebase.ocp_variant where variantType="CNV";'
    my_cursor.execute(query)
    rows = my_cursor.fetchall()
    m = ''
    counter = 0
    for row in rows:
        non_canonical_transcript = ''
        copy_change = 'Indeterminate'
        if row[3] == 'gain':
            copy_change = 'Gain'
        elif row[3] == 'loss':
            copy_change = 'Loss'
        s = f'{row[14]}: createVariantCNV(copyChange: {copy_change}, id: \\"{row[14]}\\", name: \\"{row[0]}\\", nonCanonicalTranscript: \\"{non_canonical_transcript}\\",  ),'
        m += s
        m_id = 'cnv_g_' + row[14]
        s = f'{m_id}: addVariantCNVGene(id:\\"{row[14]}\\", gene: [\\"{row[1]}\\"]),'
        m += s
        m_id = 'cnv_d_' + row[14]
        s = f'{m_id}: addVariantCNVDescription(id:\\"{row[14]}\\", description: [\\"{row[2]}\\"]),'
        m += s
        jax_variant_id = row[10]
        # addVariantSNVIndelJaxVariant(id: ID!jaxVariant: [ID!]!): String
        if jax_variant_id != None:
            m_id = 'cnv_jax_' + row[14]
            s = f'{m_id}: addVariantCNVJaxVariant(id:\\"{row[14]}\\", jaxVariant: [\\"{jax_variant_id}\\"]),'
            m += s
        go_variant_id = row[11]
        # addVariantSNVIndelGoVariant(goVariant: [ID!]!id: ID!): String
        if go_variant_id != None:
            m_id = 'cnv_go_' + row[14]
            s = f'{m_id}: addVariantCNVGoVariant(id:\\"{row[14]}\\", goVariant: [\\"{go_variant_id}\\"]),'
            m += s
        clinVarVariant = row[12]
        # addVariantSNVIndelClinVarVariant(clinVarVariant: [ID!]!id: ID!): String
        if clinVarVariant != None:
            m_id = 'cnv_cv_' + row[14]
            s = f'{m_id}: addVariantCNVClinVarVariant(id:\\"{row[14]}\\", clinVarVariant: [\\"{clinVarVariant}\\"]),'
            m += s
        hot_spot_variant_id = row[13]
        # addVariantSNVIndelHotSpotVariant(hotSpotVariant: [ID!]!id: ID!): String
        if hot_spot_variant_id != None:
            m_id = 'cnv_hot_spot_' + row[14]
            s = f'{m_id}: addVariantCNVHotSpotVariant(id:\\"{row[14]}\\", hotSpotVariant: [\\"{hot_spot_variant_id}\\"]),'
            m += s
        counter += 1
        if (counter % 100 == 0):
            send_mutation(m, server_write)
            m = ''
            print(counter)
    if m != '':
        send_mutation(m, server_write)


def write_fusions(my_cursor, server_write):
    pass


def write_ocp_variants(my_cursor, server_write):
    print('write_ocp_variants')
    write_snv(my_cursor, server_write)
    write_indels(my_cursor, server_write)
    write_cnv(my_cursor, server_write)
    # write_fusions(my_cursor, server_write)


