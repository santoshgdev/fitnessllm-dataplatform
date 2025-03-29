from pathlib import Path
from jinja2 import Template
from sqlglot import parse_one, exp


def get_delete_user_data_query(target_table: str,
                               athlete_id: str) -> str:
    """Returns a query to delete data for a specific user."""
    return f"DELETE FROM {target_table} WHERE athlete_id = '{athlete_id}'"


def get_transaction_insert_query(target_table: str,
                                 query_path: Path,
                                 parameters: dict[str, str]) -> str:
    """Returns a partitioned insert query with the given parameters.

    Args:
        target_table: The target table to insert data into.
        query_path: Query to be parameterized
        parameters: A dictionary of parameters to be replaced in the query.

    Returns:
        Atomic query string
    """
    return f"""
        BEGIN TRANSACTION;
        
        {get_delete_user_data_query(target_table=target_table,
                                    athlete_id=parameters['athlete_id'])};
        
        INSERT INTO {target_table}
        {get_parameterized_query(query_path=query_path,
                                 parameters=parameters)};
        
        COMMIT TRANSACTION;
    """



def get_parameterized_query(
    query_path: Path,
    parameters: dict[str, str],
) -> str:
    """Returns a parameterized query with the given parameters.

    Args:
        query_path: The query string to be parameterized.
        parameters: A dictionary of parameters to be replaced in the query.

    Returns:
        The parameterized query string.
    """
    with open(query_path) as f:
        query = f.read()

    template = Template(query)
    raw_sql = template.render(parameters)
    parsed = parse_one(raw_sql)
    if not parsed.find(exp.Select):
        raise ValueError("Only SELECT queries allowed")
    return raw_sql