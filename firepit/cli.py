# type: ignore[attr-defined]

"""
Typer-based CLI for testing and experimentation
"""

import csv
import json
import logging
import os
from typing import List

from tabulate import tabulate
import typer

from firepit import get_storage


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))


def defdb():
    return os.getenv('FIREPITDB', 'stix.db')


def defid():
    return os.getenv('FIREPITID', 'test-id')


app = typer.Typer(
    name="firepit",
    help="Columnar storage for STIX observations",
    add_completion=False,
)


@app.command()
def cache(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    query_id: str = typer.Argument(..., help="An identifier for this set of data"),
    filenames: List[str] = typer.Argument(..., help="STIX bundle files of query results"),
):
    """Cache STIX observation data in SQL"""
    db = get_storage(dbname, session)
    if isinstance(filenames, tuple):
        filenames = list(filenames)
    db.cache(query_id, filenames)


@app.command()
def extract(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    sco_type: str = typer.Argument(..., help="SCO type to extract"),
    query_id: str = typer.Argument(..., help="Identifier for cached data to extract from"),
    pattern: str = typer.Argument(..., help="STIX pattern to filter cached data"),
):
    """Create a view of a subset of cached data"""
    db = get_storage(dbname, session)
    db.extract(name, sco_type, query_id, pattern)


@app.command()
def filter(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    sco_type: str = typer.Argument(..., help="SCO type to extract"),
    source: str = typer.Argument(..., help="Source view"),
    pattern: str = typer.Argument(..., help="STIX pattern to filter cached data"),
):
    """Create a filtered view of a subset of cached data"""
    db = get_storage(dbname, session)
    db.filter(name, sco_type, source, pattern)


@app.command()
def assign(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    view: str = typer.Argument(..., help="View name to operate on"),
    op: str = typer.Option(..., help="Operation to perform (sort, group, etc.)"),
    by: str = typer.Option(..., help="STIX object path"),
    desc: bool = typer.Option(False, help="Sort descending"),
    limit: int = typer.Option(None, help="Max number of rows to return"),
):
    """Perform an operation on a column and name the result"""
    db = get_storage(dbname, session)
    asc = not desc
    db.assign(name, view, op, by, asc, limit)


@app.command()
def join(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    left_view: str = typer.Argument(..., help="Left view name to join"),
    left_on: str = typer.Argument(..., help="Column from left view to join on"),
    right_view: str = typer.Argument(..., help="Right view name to join"),
    right_on: str = typer.Argument(..., help="Column from right view to join on"),
):
    """Join two views"""
    db = get_storage(dbname, session)
    db.join(name, left_view, left_on, right_view, right_on)


@app.command()
def lookup(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name to look up"),
    limit: int = typer.Option(None, help="Max number of rows to return"),
    offset: int = typer.Option(0, help="Number of rows to skip"),
    format: str = typer.Option('table', help="Output format [table, json]"),
):
    """Retrieve a view"""
    db = get_storage(dbname, session)
    rows = db.lookup(name, limit=limit, offset=offset)
    if format == 'json':
        print(json.dumps(rows, separators=[',', ':']))
    else:
        print(tabulate(rows, headers='keys'))


@app.command()
def values(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    path: str = typer.Argument(..., help="STIX object path to retrieve from view"),
    name: str = typer.Argument(..., help="View name to look up"),
):
    """Retrieve the values of a STIX object path from a view"""
    db = get_storage(dbname, session)
    rows = db.values(path, name)
    for row in rows:
        print(row)


@app.command()
def tables(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
):
    """Get all view/table names"""
    db = get_storage(dbname, session)
    rows = db.tables()
    for row in rows:
        print(row)


@app.command()
def views(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
):
    """Get all view names"""
    db = get_storage(dbname, session)
    rows = db.views()
    for row in rows:
        print(row)


@app.command()
def viewdata(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    views: List[str] = typer.Argument(None, help="Views to merge"),
    format: str = typer.Option('table', help="Output format [table, json]"),
):
    """Get view data for views [default is all views]"""
    db = get_storage(dbname, session)
    rows = db.get_view_data(views)
    if format == 'json':
        print(json.dumps(rows, separators=[',', ':']))
    else:
        print(tabulate(rows, headers='keys'))


@app.command()
def columns(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name to look up"),
):
    """Get the columns names of a view/table"""
    db = get_storage(dbname, session)
    rows = db.columns(name)
    for row in rows:
        print(row)


@app.command()
def type(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name to look up"),
):
    """Get the SCO type of a view/table"""
    db = get_storage(dbname, session)
    print(db.table_type(name))


@app.command()
def schema(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name to look up"),
):
    """Get the schema of a view/table"""
    db = get_storage(dbname, session)
    rows = db.schema(name)
    print(tabulate(rows, headers='keys'))


@app.command()
def count(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name to look up"),
):
    """Get the count of rows in a view/table"""
    db = get_storage(dbname, session)
    print(db.count(name))


@app.command()
def delete(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
):
    """Delete STIX observation data in SQL"""
    db = get_storage(dbname, session)
    db.delete()


@app.command()
def sql(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    statement: str = typer.Argument(..., help="View name to look up"),
):
    """Run a SQL statement on the database [DANGEROUS!]"""
    db = get_storage(dbname, session)
    rows = db._execute(statement)
    if rows:
        print(tabulate(rows, headers='keys'))


@app.command()
def set_appdata(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name"),
    data: str = typer.Argument(..., help="Data (string)"),
):
    """Set the app-specific data for a view"""
    db = get_storage(dbname, session)
    db.set_appdata(name, data)


@app.command()
def get_appdata(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="View name"),
):
    """Get the app-specific data for a view"""
    db = get_storage(dbname, session)
    print(db.get_appdata(name))


@app.command()
def load(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    sco_type: str = typer.Option(None, help="SCO type of data to load"),
    query_id: str = typer.Option(None, help="An identifier for this set of data"),
    preserve_ids: str = typer.Option(True, help="Use IDs in the data"),
    filename: str = typer.Argument(..., help="Data file to load (JSON only)"),
):
    """Cache STIX observation data in SQL"""
    db = get_storage(dbname, session)
    try:
        with open(filename, 'r') as fp:
            data = json.load(fp)
    except json.decoder.JSONDecodeError:
        with open(filename, 'r') as fp:
            data = list(csv.DictReader(fp))
    db.load(name, data, sco_type, query_id, preserve_ids)


@app.command()
def reassign(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    filename: str = typer.Argument(..., help="Data file to load (JSON only)"),
):
    """Update/replace STIX observation data in SQL"""
    db = get_storage(dbname, session)
    with open(filename, 'r') as fp:
        data = json.load(fp)
    db.reassign(name, data)


@app.command()
def merge(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name for this new view"),
    views: List[str] = typer.Argument(..., help="Views to merge"),
):
    """Merge 2 or more views into a new view"""
    db = get_storage(dbname, session)
    db.merge(name, views)


@app.command()
def remove(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    name: str = typer.Argument(..., help="Name of view to remove"),
):
    """Remove a view"""
    db = get_storage(dbname, session)
    db.remove_view(name)


@app.command()
def rename(
    dbname: str = typer.Option(defdb(), help="Path/name of database"),
    session: str = typer.Option(defid(), help="Session ID to data separation"),
    oldname: str = typer.Argument(..., help="Name of view to rename"),
    newname: str = typer.Argument(..., help="New name of view to rename"),
):
    """Remove a view"""
    db = get_storage(dbname, session)
    db.rename_view(oldname, newname)


if __name__ == "__main__":
    app()
