from ws.haemera.action import Action
import json
import sqlalchemy.engine
import transaction


def test_rowproxy_is_treated_as_dict(db):
    act = Action()
    act.subject = 'test'
    db.add(act)
    transaction.commit()
    row = Action.find_by_sql('1')[0]
    assert isinstance(row, sqlalchemy.engine.RowProxy)
    assert '"subject": "test"' in json.dumps(row)
