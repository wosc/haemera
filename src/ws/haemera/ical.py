from pyramid.view import view_config
from ws.haemera.action import Action
import pendulum
import vobject
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
    date = pendulum.parse(
        action['timestamp'] + ' ' + action['start_time'], tz='Europe/Berlin')
    duration = pendulum.parse(action['duration'])
    event.add('dtstart').value = date
    event.add('dtend').value = date.add(
        hours=duration.hour, minutes=duration.minute)
    event.add('status').value = 'CONFIRMED'
