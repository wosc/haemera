from pyramid.view import view_config
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.sql import text as sql
import json
import ws.haemera.db
import ws.haemera.interfaces
import zope.component
import zope.sqlalchemy


class Action(ws.haemera.db.Object):

    subject = Column(String)
    topic = Column(String)
    priority = Column(Integer, server_default='0')
    status = Column(String, server_default='todo')
    body = Column(Text)


@view_config(
    route_name='listing',
    renderer='templates/listing.html')
def listing(request):
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session
    rows = db.execute(sql(
        'SELECT * FROM action ORDER BY priority DESC, topic, subject')
    ).fetchall()
    return {'actions': [dict(x) for x in rows]}


@view_config(
    route_name='update',
    request_method='POST',
    renderer='json')
def update(request):
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session
    for action in json.loads(request.body):
        if action.get('status') == 'deleted':
            db.execute(Action.__table__.delete().where(
                Action.id == action['id']))
        elif not action.get('id'):
            db.execute(Action.__table__.insert().values(**action))
        else:
            db.execute(Action.__table__.update().where(
                Action.id == action['id']).values(**action))
    zope.sqlalchemy.mark_changed(db)
    return {}
