

def create_jax_variant():
    rows = 'name, description_id, jax_Id, jaxGene_gene_Id, pDot, cDot, gDot, transcript, variantType, proteinEffect, id'
    mutation = '''createJaxVariant(
    cDot: String!
    gDot: String!
    id: ID!
    jaxId: String!
    name: String!
    pDot: String!
    proteinEffect: String!
    transcript: String!
    variantType: String!
    ): String'''
    create_mutation(mutation, rows, 'jv')

def create_hotspot_variant():
    rows = 'name, gene, referenceAminoAcid, variantAminoAcid, begin, end, position, id'
    mutation = '''createHotSpotVariant(
begin: String!
end: String!
gene: String!
id: ID!
name: String!
position: Int!
referenceAminoAcid: String!
variantAminoAcid: String!
): String'''
    create_mutation(mutation, rows, 'row')

def create_clinvar_variant():
    rows = 'xid, variantID, gene, pDot, cDot, significance, signficanceExplanation, cdot_pos, pdot_pos, id'
    mutation = '''createClinVarVariant(
cDot: String!
gene: String!
id: ID!
pDot: String!
signficanceExplanation: String!
significance: String!
variantID: String!
): String    '''
    create_mutation(mutation, rows, 'row')


def create_oncotree_occurrence():
    rows = 'xid, disease, oncoTreeCode, percentOccurrence, perThousandOccurrence, occurrences, totalSamples, id'
    mutation = '''createOncoTreeOccurrence(
disease: String!
id: ID!
occurrences: Int!
oncoTreeCode: String!
percentOccurrence: String!
totalSamples: Int!
perThousandOccurrence: Int!
): String'''
    create_mutation(mutation, rows, 'otc')

def create_go_variant():
    rows = 'name, gene, goID, mutationType, jaxVariant_Id, id'
    mutation = '''createGOVariant(
gene: String!
goID: String!
id: ID!
mutationType: String!
name: String!
): String'''
    create_mutation(mutation, rows, 'row')

def create_snv_variant():
    rows = 'name, omniGene_gene_Id, description_id, pDot, cDot, gDot, regionType, indelType, variantType, proteinEffect, jax_variant_Id, go_variant_Id, clinvar_variant_Id, hot_spot_variant_Id, id'
    mutation = f'''createVariantSNVIndel(
cDot: String!
gDot: String!
id: ID!
indelType: IndelType!
name: String!
nonCanonicalTranscript: String
pDot: String!
proteinEffect: VariantProteinEffect!
variantType: VariantType!
): String'''
    create_mutation(mutation, rows, 'row')


def create_mutation(mutation, rows, row_name):
    columns = rows.split(',')
    cols_dict = {}
    for idx, col in enumerate(columns):
        cols_dict[col.strip().replace('_', '')] = str(idx)
    m_elems = mutation.split('\n')
    params = []
    types_dict = {}
    for elem in m_elems[1:-1]:
        p = elem.lstrip().split(':')[0]
        t = elem.split(':')[1].lstrip()
        params.append(p)
        types_dict[p] = t
    if 'id' in cols_dict:
        result = '{' + row_name + '[' + cols_dict['id'] + ']}: '
    else:
        result = '{'  + row_name + '[?]}: '
    result += m_elems[0]
    for p in params:
        if p in cols_dict:
            index = cols_dict[p]
        else:
            index = '?'
        t = types_dict[p]
        if t.startswith('Int'):
            s = p + ': {' + row_name + '[' + index + ']}, '
        else:
            s = p + ': \\\\"{'  + row_name + '[' + index + ']}\\\\", '
        result += s
    result += '),'
    print(result)


def main():
    create_jax_variant()
    # create_hotspot_variant()
    # create_clinvar_variant()
    # create_oncotree_occurrence()
    # create_go_variant()
    # create_snv_variant()

if __name__ == "__main__":
    main()