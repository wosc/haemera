import pendulum
import pytest
import ws.haemera.db
import zope.component


@pytest.fixture()
def db(request):
    db = ws.haemera.db.Database('sqlite:///', testing=True)
    zope.component.provideUtility(db)
    db.initialize_database()
    request.addfinalizer(
        lambda: zope.component.getSiteManager().unregisterUtility(db))
    return db


@pytest.fixture()
def clock(request):
    request.addfinalizer(pendulum.set_test_now)
    return lambda x: pendulum.set_test_now(x)
