from sqlalchemy import Column, Integer, String, Text
import ws.haemera.db


class Action(ws.haemera.db.Object):

    subject = Column(String)
    topic = Column(String)
    priority = Column(Integer, server_default='0')
    status = Column(String, server_default='todo')
    body = Column(Text)
