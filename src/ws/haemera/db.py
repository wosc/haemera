from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import text as sql
import pendulum
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.orm
import transaction
import ws.haemera.interfaces
import zope.interface
import zope.sqlalchemy


@zope.interface.implementer(ws.haemera.interfaces.IDatabase)
class Database(object):

    def __init__(self, dsn, testing=False):
        self.engine = sqlalchemy.create_engine(dsn)
        self.session_factory = sqlalchemy.orm.scoped_session(
            sqlalchemy.orm.sessionmaker(bind=self.engine))
        zope.sqlalchemy.register(self.session_factory, keep_session=testing)

    def initialize_database(self):
        from .action import Action
        try:
            with transaction.manager:
                Action.query().all()
        except Exception:
            pass
        else:
            raise ValueError(
                'Database already exists, refusing to initialize again.')
        Object.metadata.create_all(self.engine)

    @property
    def session(self):
        return self.session_factory()

    def add(self, obj):
        return self.session.add(obj)

    def delete(self, obj):
        return self.session.delete(obj)

    def query(self, *args, **kw):
        return self.session.query(*args, **kw)


class ObjectBase(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    def __iter__(self):
        from datetime import date, datetime
        for c in self.__table__.columns:
            value = getattr(self, c.name)
            if isinstance(value, (date, datetime)):
                value = str(value)
            yield(c.name, value)

    @staticmethod
    def db():
        return zope.component.getUtility(ws.haemera.interfaces.IDatabase)

    @classmethod
    def query(cls):
        return cls.db().query(cls)

    @classmethod
    def find_by_id(cls, id):
        return cls.db().query(cls).get(id)

    @classmethod
    def find_by_sql(cls, text, **params):
        return cls.db().session.execute(
            cls.__table__.select().where(sql(text)),
            params=params).fetchall()


DeclarativeBase = sqlalchemy.ext.declarative.declarative_base(
    cls=ObjectBase)


class Object(DeclarativeBase):

    __abstract__ = True

    id = Column(Integer, primary_key=True)


class DateTime(sqlalchemy.types.TypeDecorator):
    # Adapted from <https://github.com/mozilla/build-relengapi/
    #   blob/master/relengapi/lib/db.py>

    impl = sqlalchemy.types.DateTime

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, pendulum.DateTime) or value.tzinfo is None:
            raise ValueError('datetime with timezone required, got %s' % value)
        value = value.in_tz('UTC')
        # MySQL stores datetimes without any timezone information. Its type
        # conversion is based on exact classes, so pendulum instances fall
        # through. Then their str() causes (1292, "Incorrect datetime value").
        # Since it's somewhat cleaner, we fix it at sqlalchemy level instead.
        if dialect.name == 'mysql':
            value = value.replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):
        # We expect UTC dates back, so populate with tzinfo
        if value is not None:
            return value.replace(tzinfo=pendulum.timezone('UTC'))
