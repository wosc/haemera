from pyramid.view import view_config
from sqlalchemy import Column, Date, DateTime, Integer, String, Text
from sqlalchemy.sql import text as sql
import json
import pendulum
import ws.haemera.db
import ws.haemera.interfaces
import zope.component
import zope.sqlalchemy


class Action(ws.haemera.db.Object):

    subject = Column(String)
    body = Column(Text)

    topic = Column(String)
    priority = Column(Integer, server_default='0')

    project = Column(String)

    # inactive, todo, scheduled, recurring, done
    status = Column(String, server_default='todo')
    # status=done
    done_at = Column(DateTime)

    # status=scheduled, recurring
    timestamp = Column(Date)
    start_time = Column(String)  # HH:MM
    duration = Column(String)    # HH:MM
    delegate = Column(String)

    @classmethod
    def find_by_sql(cls, text):
        return cls.db().session.execute(sql(text)).fetchall()


@view_config(
    route_name='listing',
    renderer='templates/listing.html')
def listing(request):
    conf = zope.component.getUtility(ws.haemera.interfaces.ISettings)
    rows = Action.find_by_sql(conf.listing_queries[request.matchdict['query']])
    return {'actions': [dict(x) for x in rows]}


@view_config(
    route_name='update',
    request_method='POST',
    renderer='json')
def update(request):
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session
    for action in json.loads(request.body):
        # XXX Use a proper schema?
        if action.get('timestamp'):
            action['timestamp'] = pendulum.parse(action['timestamp'])
        for key, value in action.items():
            # XXX I think this is actually a vue shortcoming
            if value == '':
                action[key] = None

        if action.get('status') == 'deleted':
            db.execute(Action.__table__.delete().where(
                Action.id == action['id']))
        elif not action.get('id'):
            db.execute(Action.__table__.insert().values(**action))
        else:
            if action['status'] == 'done':
                action['done_at'] = pendulum.now('UTC')
            db.execute(Action.__table__.update().where(
                Action.id == action['id']).values(**action))
    zope.sqlalchemy.mark_changed(db)
    return {}
