from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from sqlalchemy import Column, String, Text
from ws.haemera.db import DateTime
import pendulum
import ws.haemera.action
import ws.haemera.db
import zope.component
import zope.sqlalchemy


class Project(ws.haemera.db.Object):

    subject = Column(String(255), index=True)
    body = Column(Text)
    topic = Column(String(20))
    # todo, done
    status = Column(String(20), server_default='todo', index=True)
    # status=done
    done_at = Column(DateTime)

    @classmethod
    def all(cls):
        result = []
        for project in cls.find_by_sql("status = 'todo' ORDER BY subject"):
            project = dict(project)
            parts = project['subject'].split('|')
            prefix = '&raquo;  ' * (len(parts) - 1)
            project['subject'] = prefix + parts[-1]
            result.append(project)
        return result


@view_config(
    route_name='project',
    renderer='templates/project/show.html')
def show(request):
    selected = request.matchdict['project']
    done = " AND status = 'todo'" if not request.params.get('done') else ''
    if selected == 'root':
        project = {'subject': 'root', 'topic': 'none', 'id': 'root'}
        children = Project.find_by_sql(
            "subject not like '%|%'" + done + " ORDER BY subject")
    else:
        project = Project.find_by_sql('id=:id', id=selected)[0]
        children = Project.find_by_sql(
            'subject like :p ' + done + ' ORDER BY subject',
            p='%s|%%' % project['subject'])
    result = {
        'project': project,
        'children': children,
    }
    result.update(ws.haemera.action.project_actions(request))
    return result


@view_config(
    route_name='project_edit',
    renderer='templates/project/edit.html')
def edit(request):
    return {'context': Project.find_by_id(request.matchdict['project'])}


@view_config(
    route_name='project_new',
    renderer='templates/project/edit.html')
def new(request):
    return {'context': {}}


@view_config(
    route_name='project_edit',
    request_method='POST')
@view_config(
    route_name='project_new',
    request_method='POST')
def store(request):
    id = request.matchdict.get('project')
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase).session

    if 'delete' in request.POST:
        db.execute(Project.__table__.delete().where(Project.id == id))
        zope.sqlalchemy.mark_changed(db)
        return HTTPFound(location=request.route_url('project', project='root'))

    data = {
        'subject': request.POST['subject'],
        'body': request.POST['body'].strip(),
        'topic': request.POST['topic'],
        'status': request.POST['status'],
    }
    if id:
        if data['status'] == 'done':
            data['done_at'] = pendulum.now('UTC')
        db.execute(Project.__table__.update().where(
            Project.id == id).values(**data))
    else:
        result = db.execute(Project.__table__.insert().values(**data))
        id = result.inserted_primary_key[0]
    zope.sqlalchemy.mark_changed(db)
    return HTTPFound(location=request.route_url('project', project=id))
