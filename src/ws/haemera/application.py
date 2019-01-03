from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
import jinja2
import json
import os.path
import pkg_resources
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
        self.settings['version'] = pkg_resources.get_distribution(
            'ws.haemera').version
        zope.component.provideUtility(
            self.settings, ws.haemera.interfaces.ISettings)

        db = ws.haemera.db.Database(self.settings['sqlalchemy.url'])
        zope.component.provideUtility(db)

        registry = pyramid.registry.Registry(
            bases=(zope.component.getGlobalSiteManager(),))
        self.config = pyramid.config.Configurator(registry=registry)
        self.config.setup_registry(settings=self.settings)
        # setup_registry() insists on copying the settings mapping into a new
        # `pyramid.config.settings.Settings` instance, sigh.
        self.settings.update(self.config.registry.settings)
        self.config.registry.settings = self.settings

        self.config.include('pyramid_tm')
        self.configure_jinja()

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

        c.add_route('listing', '/actions/{query}')

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
    pass


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
    raise HTTPFound(location=request.route_url('listing', query='todo'))
