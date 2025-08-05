from pyramid.authentication import AuthTktAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy, Allow, Authenticated
from pyramid.decorator import reify
from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.view import view_config
import collections
import importlib.metadata
import jinja2
import json
import os.path
import pyramid.config
import pyramid.paster
import pyramid.registry
import pyramid_jinja2
import re
import sys
import transaction
import ws.haemera
import ws.haemera.db
import ws.haemera.interfaces
import ws.haemera.serializer  # activate monkeypatches
import zope.component
import zope.interface


class Application(object):

    DONT_SCAN = [re.compile('tests$').search]

    def __call__(self, global_conf, **settings):
        self.configure_pyramid(settings)
        self.configure_routes()
        return self.config.make_wsgi_app()

    def configure_pyramid(self, settings):
        self.settings = Settings()
        self.settings.update(settings)
        self.settings['version'] = importlib.metadata.version(
            'ws.haemera')
        zope.component.provideUtility(
            self.settings, ws.haemera.interfaces.ISettings)

        db = ws.haemera.db.Database(self.settings['sqlalchemy.url'])
        zope.component.provideUtility(db)

        registry = pyramid.registry.Registry(
            bases=(zope.component.getGlobalSiteManager(),))
        c = self.config = pyramid.config.Configurator(registry=registry)
        c.setup_registry(settings=self.settings)
        # setup_registry() insists on copying the settings mapping into a new
        # `pyramid.config.settings.Settings` instance, sigh.
        self.settings.update(c.registry.settings)
        c.registry.settings = self.settings

        c.include('pyramid_tm')
        self.configure_jinja()

        if self.settings.get('auth.secret'):
            c.set_authentication_policy(AuthTktAuthenticationPolicy(
                self.settings['auth.secret'],
                cookie_name='haemera_auth', max_age=30 * 24 * 3600))
            c.set_authorization_policy(ACLAuthorizationPolicy())
            c.set_root_factory(ACLRoot)

    def configure_jinja(self):
        c = self.config

        # We don't use include('pyramid_jinja2') since that already sets up a
        # renderer for `.jinja2` files which we don't want.
        c.add_directive(
            'add_jinja2_renderer', pyramid_jinja2.add_jinja2_renderer)
        c.add_directive(
            'add_jinja2_search_path', pyramid_jinja2.add_jinja2_search_path)
        c.add_directive(
            'add_jinja2_extension', pyramid_jinja2.add_jinja2_extension)
        c.add_directive(
            'get_jinja2_environment', pyramid_jinja2.get_jinja2_environment)

        c.add_jinja2_renderer('.html')
        c.add_jinja2_search_path('ws.haemera:', '.html')

        c.commit()
        env = self.config.get_jinja2_environment('.html')
        env.filters['json'] = tojson

    def configure_routes(self):
        c = self.config

        c.add_route('home', '/')
        c.add_route('login', '/login')
        c.add_route('logout', '/logout')

        c.add_route('action_list', '/list/{query}')
        c.add_route('ical', '/ical/{query}')
        c.add_route('update', '/actions/update')

        c.add_route('project_actions', '/project/list/{project}')
        c.add_route('project_new', '/project/new')
        c.add_route('project_edit', '/project/{project}/edit')
        c.add_route('project_delete', '/project/{project}/delete')
        c.add_route('project', '/project/{project}')

        c.add_route('topic_css', '/static/css/topic.css')

        c.add_static_view('static', 'ws.haemera:static')

        c.scan(package=ws.haemera, ignore=self.DONT_SCAN)


app_factory = Application()


def tojson(value):
    if isinstance(value, jinja2.Undefined):
        return 'null'
    result = json.dumps(value)
    # <https://html.spec.whatwg.org/multipage
    #  /scripting.html#restrictions-for-contents-of-script-elements>
    result = result.replace('<script', r'<\script')
    result = result.replace('</script', r'<\/script')
    return result


@zope.interface.implementer(ws.haemera.interfaces.ISettings)
class Settings(dict):

    @reify
    def listing_queries(self):
        result = collections.OrderedDict()
        for key, value in self.items():
            if key.startswith('query.'):
                result[key.replace('query.', '', 1)] = value
        return result

    @reify
    def topics(self):
        result = collections.OrderedDict()
        for key, value in self.items():
            if key.startswith('topic.'):
                result[key.replace('topic.', '', 1)] = value
        return result


def initialize_database(argv=sys.argv):
    if len(argv) != 2:
        sys.stderr.write('usage: %s <my.ini>\n' % os.path.basename(argv[0]))
        sys.exit(1)
    config = argv[1]
    pyramid.paster.setup_logging(config)
    settings = pyramid.paster.get_appsettings(config)
    app_factory(None, **settings)
    db = zope.component.getUtility(ws.haemera.interfaces.IDatabase)
    with transaction.manager:
        db.initialize_database()


@view_config(route_name='home')
def home(request):
    raise HTTPFound(location=request.route_url('action_list', query='todo'))


@view_config(
    route_name='topic_css',
    renderer='string')
def topic_css(request):
    conf = zope.component.getUtility(ws.haemera.interfaces.ISettings)
    request.response.content_type = 'text/css'
    return '\n'.join('.topic-%s { color: #%s; }' % (key, value)
                     for key, value in conf.topics.items())


class ACLRoot(object):

    __acl__ = [(Allow, Authenticated, 'view',)]

    def __init__(self, request):
        pass


@view_config(
    route_name='login',
    renderer='templates/login.html')
def login(request):
    if request.method == 'POST':
        conf = zope.component.getUtility(ws.haemera.interfaces.ISettings)
        if (request.POST.get('username') == conf['auth.username'] and
                request.POST.get('password') == conf['auth.password']):
            headers = pyramid.security.remember(
                request, request.POST['username'])
            raise HTTPFound(
                request.route_url('action_list', query='todo'),
                headers=headers)
    return {}


@view_config(context=HTTPForbidden)
def forbidden(request):
    return HTTPFound(request.route_url('login'))


@view_config(route_name='logout')
def logout(request):
    headers = pyramid.security.forget(request)
    raise HTTPFound(request.route_url('login'), headers=headers)
