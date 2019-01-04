from sqlalchemy import Column, Integer
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.sql import text as sql
import sqlalchemy
import sqlalchemy.exc
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
            sqlalchemy.orm.sessionmaker(
                bind=self.engine,
                extension=zope.sqlalchemy.ZopeTransactionExtension(
                    keep_session=testing)))

    def initialize_database(self):
        from .action import Action
        try:
            with transaction.manager:
                Action.query().all()
        except sqlalchemy.exc.OperationalError:
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
        return cls.db().session.execute(sql(text), params=params).fetchall()


DeclarativeBase = sqlalchemy.ext.declarative.declarative_base(
    cls=ObjectBase)


class Object(DeclarativeBase):

    __abstract__ = True

    id = Column(Integer, primary_key=True)
