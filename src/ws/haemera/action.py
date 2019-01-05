from pyramid.view import view_config
from sqlalchemy import Column, Date, Integer, String, Text
from ws.haemera.db import DateTime
from ws.haemera.project import Project
import json
import pendulum
import ws.haemera.db
import ws.haemera.interfaces
import zope.component
import zope.sqlalchemy


class Action(ws.haemera.db.Object):

    subject = Column(String(255))
    body = Column(Text)

    topic = Column(String(20))
    priority = Column(Integer, server_default='0')

    project = Column(String(255), index=True)

    # inactive, todo, scheduled, recurring, done
    status = Column(String(20), server_default='todo', index=True)
    # status=done
    done_at = Column(DateTime)

    # status=scheduled, recurring
    timestamp = Column(Date, index=True)
    start_time = Column(String(5))  # HH:MM
    duration = Column(String(5))    # HH:MM
    delegate = Column(String(255), index=True)

    # status=recurring
    rrule = Column(String(255))
    latest_instance = Column(Date)
    template = Column(Integer)


@view_config(
    route_name='action_list',
    renderer='templates/actionlist.html')
def list(request):
    conf = zope.component.getUtility(ws.haemera.interfaces.ISettings)
    rows = Action.find_by_sql(conf.listing_queries[request.matchdict['query']])

    # XXX Using the name of the query is a kludge.
    if request.matchdict.get('query') in ['waiting', 'scheduled']:
        result = []
        for row in rows:
            row = dict(row)
            display_timestamp = row['timestamp'].strftime('%a, %d.%m.%Y')
            if row['start_time']:
                display_timestamp += ' ' + row['start_time']
            row['display_timestamp'] = display_timestamp
            result.append(row)
        rows = result

    return {
        'actions': rows,
        'projects': Project.all(),
    }


@view_config(
    route_name='project_actions',
    renderer='templates/actionlist.html')
def project_actions(request):
    done = " AND status <> 'done'" if not request.params.get('actdone') else ''
    rows = Action.find_by_sql(
        "project=:project AND status <> 'recurring'" + done +
        " ORDER BY status, id",
        project=request.matchdict['project'])
    return {
        'actions': rows,
        'projects': Project.all(),
    }


@view_config(
    route_name='update',
    request_method='POST',
    renderer='json')
def update(request):
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session
    for action in json.loads(request.body):
        # XXX Use a proper schema?
        if action.get('timestamp'):
            action['timestamp'] = pendulum.parse(action['timestamp']).date()
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
