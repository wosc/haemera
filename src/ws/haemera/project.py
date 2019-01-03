from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
from sqlalchemy import Column, String, Text
import ws.haemera.db
import zope.component
import zope.sqlalchemy


class Project(ws.haemera.db.Object):

    subject = Column(String, index=True)
    body = Column(Text)
    topic = Column(String)

    @classmethod
    def all(cls):
        result = []
        for project in cls.find_by_sql(
                'SELECT id, subject, topic FROM project ORDER BY subject'):
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
    if selected == 'root':
        project = {'subject': 'root', 'topic': 'none'}
        children = Project.find_by_sql(
            "SELECT * FROM project WHERE subject not like '%|%'"
            " ORDER BY subject")
    else:
        project = Project.find_by_sql(
            'SELECT * FROM project WHERE id=:id', id=selected)[0]
        children = Project.find_by_sql(
            'SELECT * FROM project WHERE subject like :p ORDER BY subject',
            p='%s|%%' % project['subject'])
    return {
        'project': project,
        'children': children,
    }


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
    }
    if id:
        db.execute(Project.__table__.update().where(
            Project.id == id).values(**data))
    else:
        result = db.execute(Project.__table__.insert().values(**data))
        id = result.inserted_primary_key[0]
    zope.sqlalchemy.mark_changed(db)
    return HTTPFound(location=request.route_url('project', project=id))
