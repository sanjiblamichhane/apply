"""The tables: every row someone owns says whose it is."""

from apply.store.sql.models import UNOWNED, Base


def test_every_table_but_accounts_and_the_queue_has_an_owner():
    for table in Base.metadata.sorted_tables:
        if table.name in UNOWNED:
            continue
        assert "owner_id" in table.c, f"{table.name} has no owner_id"
        assert table.c.owner_id.index or any("owner_id" in [c.name for c in ix.columns] for ix in table.indexes), (
            f"{table.name}.owner_id is not indexed"
        )


def test_ids_are_ulids():
    for table in Base.metadata.sorted_tables:
        assert table.c.id.type.length == 26, table.name
