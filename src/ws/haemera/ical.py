from pyramid.view import view_config
from ws.haemera.action import Action
import dateutil.rrule
import os.path
import pendulum
import pyramid.paster
import sys
import transaction
import vobject
import ws.haemera.application
import ws.haemera.interfaces
import zope.component


@view_config(
    route_name='ical',
    renderer='string')
def export_ical(request):
    conf = zope.component.getUtility(ws.haemera.interfaces.ISettings)
    query = request.matchdict['query']
    if 'ical.' + query in conf:
        query = conf['ical.' + query]
    else:  # Try UI queries as well
        query = conf.listing_queries[query]

    cal = vobject.iCalendar()
    for row in Action.find_by_sql(query):
        event = cal.add('vevent')
        to_ics(event, row)
    return cal.serialize()


def to_ics(event, action):
    event.add('uid').value = 'id-%s' % action['id']
    event.add('summary').value = action['subject']
    event.add('description').value = action['body']
    date = pendulum.parse(
        str(action['timestamp']) + ' ' + action['start_time'],
        tz='Europe/Berlin')
    duration = pendulum.parse(action['duration'])
    event.add('dtstart').value = date
    event.add('dtend').value = date.add(
        hours=duration.hour, minutes=duration.minute)
    event.add('status').value = 'CONFIRMED'


def instantiate_recurring(argv=sys.argv):
    if len(argv) != 2:
        sys.stderr.write('usage: %s <my.ini>\n' % os.path.basename(argv[0]))
        sys.exit(1)
    config = argv[1]
    pyramid.paster.setup_logging(config)
    settings = pyramid.paster.get_appsettings(config)
    ws.haemera.application.app_factory(None, **settings)
    for template in Action.query().filter_by(status='recurring'):
        with transaction.manager:
            _instantiate_recurring(template)


def _instantiate_recurring(template):
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session
    today = pendulum.today().date()

    latest = template.latest_instance
    if not latest:
        start = template.timestamp
        skip = 0
    else:
        latest = template.latest_instance
        start = latest
        # rrule generates the first occurence on `dtstart`.
        skip = 1
        if latest > today:
            return

    rule = dateutil.rrule.rrulestr(template.rrule, dtstart=start)
    rule = rule.replace(count=1 + skip)
    generated = list(rule)

    for date in generated[skip:]:
        action = dict(template)
        del action['rrule']
        del action['latest_instance']
        action['template'] = action.pop('id')
        action['status'] = 'scheduled'
        action['timestamp'] = date

        db.execute(Action.__table__.insert().values(**action))

    template.latest_instance = date
    db.add(template)  # XXX why?
    zope.sqlalchemy.mark_changed(db)
