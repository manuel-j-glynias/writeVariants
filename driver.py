import datetime

from clinvar_variant import create_clinvar_db
from create_GO_variant_db import create_go_variant_db
from create_jax_variant_db import create_jax_variant_db
from full_extractor_sql import extract
from oncotree import create_hot_spot_variants
from write_ocp_variants import create_ocp_variant_db
from write_variants import build_graphql_from_sql


def main():
    print('start driver at:', datetime.datetime.now().strftime("%H:%M:%S"))
    extract()

    # populate mysql databases
    create_jax_variant_db()
    create_go_variant_db()
    create_clinvar_db()
    create_hot_spot_variants()
    create_ocp_variant_db()

    # write to graphql
    build_graphql_from_sql()
    print('end driver at:', datetime.datetime.now().strftime("%H:%M:%S"))


if __name__ == "__main__":
    main()