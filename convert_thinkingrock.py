from ws.haemera.action import Action
from ws.haemera.project import Project
import logging
import lxml.objectify
import os.path
import pendulum
import pyramid.paster
import sys
import transaction
import ws.haemera.application
import zope.sqlalchemy


log = logging.getLogger('ws.haemera.import')
WEEKDAYS = ['1-based', 'SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA']

PROJECTS = []
db = None


def main():
    if len(sys.argv) != 3:
        sys.stderr.write(
            'usage: %s my.ini tr.xml\n' % os.path.basename(sys.argv[0]))
        sys.exit(1)

    config = sys.argv[1]
    pyramid.paster.setup_logging(config)
    settings = pyramid.paster.get_appsettings(config)
    ws.haemera.application.app_factory(None, **settings)
    global db
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session

    doc = lxml.objectify.parse(open(sys.argv[2])).getroot()
    clean_up_xml(doc)

    # Ensure 'Work' gets id=1 since it has special meaning (as haemera doesn't
    # use contexts).
    PROJECTS.append({
        'subject': 'Work', 'topic': 'work', 'status': 'todo', 'body': 'null'})
    for project in doc.xpath('/data/rootProject/children/project'):
        convert_project(project)

    for i, project in enumerate(PROJECTS):
        if project['subject'] == 'Single Actions':
            continue

        project['id'] = i + 1
        with transaction.manager:
            db.execute(Project.__table__.insert().values(**project))
            zope.sqlalchemy.mark_changed(db)


def convert_project(project):
    subject = project.description.text
    node = project
    while node.tag != 'rootProject':
        node = node.getparent()
        if node.tag == 'project':
            subject = '%s|%s' % (node.description, subject)

    log.info('Processing %s', subject)
    proj = {
        'subject': subject,
        'body': project.purpose.text or None,
        'topic': topic(project),
    }
    if project.done:
        proj['status'] = 'done'
        proj['done_at'] = date(project.doneDate)
    else:
        proj['status'] = 'todo'
    PROJECTS.append(proj)

    project_id = len(PROJECTS)
    if project.description == 'Single Actions':
        project_id = None
    for action in project.xpath('children/action'):
        data = {
            'subject': action.description.text,
            'body': action.notes.text or None,
            'topic': topic(action),
            'status': 'todo',
            'project': project_id,
        }

        if 'context[6]' in action.context.get('reference', 'none'):
            data['project'] = 1  # work

        if action.find('priority') is not None:
            if 'action[9]/priority' in action.priority.get('reference', ''):
                data['priority'] = '50'
            elif 'action/priority' in action.priority.get('reference', ''):
                data['priority'] = '100'

        if action.state.find('recurrence') is not None:
            rec = action.state.recurrence
            if rec.get('reference'):
                # This is an instance of a recurrence, which we'll generate
                # ourselves
                continue
            data['status'] = 'recurring'
            data['subject'] = rec.description.text
            data['topic'] = topic(rec)
            # The only frequency where the start date really matters is
            # "every x days", and I'm not very fussed about that one either.
            # So we just pretend all of these just now started afresh.
            data['timestamp'] = pendulum.today().subtract(days=1)
            data['start_time'] = '%02d:%02d' % (
                rec.scheduleHours, rec.scheduleMins)
            data['duration'] = '%02d:%02d' % (
                rec.durationHours, rec.durationMins)

            # Just enough "parsing" to handle the cases that I actually used.
            period = rec.period.get('class')
            if period == 'tr.model.action.PeriodDay':
                data['rrule'] = 'FREQ=DAILY;INTERVAL=%s' % rec.frequency
            elif period == 'tr.model.action.PeriodWeek':
                days = ','.join([WEEKDAYS[x.pyval] for x in rec.xpath(
                    'period/selectedDays/int')])
                data['rrule'] = 'FREQ=WEEKLY;BYDAY=%s' % days
            elif period == 'tr.model.action.PeriodMonth':
                if rec.period.option == 'Each':
                    data['rrule'] = 'FREQ=MONTHLY;BYMONTHDAY=' + ','.join([
                        x.text for x in rec.xpath('period/selectedDays/int')])
                elif rec.period.option == 'OnThe':
                    data['rrule'] = 'FREQ=MONTHLY;BYDAY=%s(%s)' % (
                        rec.period.onTheDay.text[:2].upper(),
                        rec.period.selectedDays.int)
        elif action.done:
            data['status'] = 'done'
            data['done_at'] = date(action.doneDate)
        elif action.state.get('class') == 'actionStateInactive':
            data['status'] = 'inactive'
        elif action.state.get('class') == 'actionStateDelegated':
            if '2039-12-31' in action.state.chase.text:  # funky special usage
                data['status'] = 'inactive'
            else:
                data['status'] = 'scheduled'
                data['delegate'] = action.state.to.text or ''
                data['timestamp'] = date(action.state.chase).date()
        elif action.state.get('class') == 'actionStateScheduled':
            data['status'] = 'scheduled'
            ts = date(action.state.date)
            data['timestamp'] = ts.date()
            data['start_time'] = ts.strftime('%H:%M')
            data['duration'] = '%02d:%02d' % (
                action.state.durationHours, action.state.durationMinutes)

        with transaction.manager:
            db.execute(Action.__table__.insert().values(**data))
            zope.sqlalchemy.mark_changed(db)

    for child in project.xpath('children/project'):
        convert_project(child)


def topic(node):
    result = node.getroottree().getroot().xpath(
        node.topic.get('reference', '/invalid'))
    if not result:
        return 'none'
    return result[0].name.text.lower()


def date(node):
    return pendulum.parse(node.text.replace(' UTC', 'Z'))


def clean_up_xml(doc):
    # Resolve strange references
    for done in doc.xpath('//doneDate[@reference]'):
        # For _some_ things the lxml API is really clumsy...
        done.getparent().doneDate = doc.xpath(done.get('reference'))[0].text

    # Treat "Future" and "Single Actions" like any other project
    future = doc.rootFutures
    future.tag = 'project'
    future.description = 'Future'
    doc.rootProject.children.append(future)

    single = doc.rootProject.parent
    single.description = 'Single Actions'
    single.tag = 'project'
    children = single.children.actions.children
    single.remove(single.children)
    single.append(children)
    doc.rootProject.children.append(single)


if __name__ == '__main__':
    main()
