# Taken from <https://bitbucket.org/gocept/risclog.sqlalchemy
#   /src/tip/src/risclog/sqlalchemy/serializer.py>
import datetime
import decimal
import json
import sqlalchemy.engine


def datetime_encode(o):
    return o.isoformat()


def decimal_encode(o):
    return str(o)


class DictWrapper(dict):
    """Make stupid stdlib json treat dict-like things like, well, dicts.
    This way we still incur an additional dict object for each row, but
    at least don't have to *copy* all items, as we would with `dict(row)`.

    It would be so much nicer if you could properly register "type -> function"
    to do the encoding (and reuse existing functions!), then we could simply
    say "RowProxy -> stdlib default dict function".
    """

    def __init__(self, context):
        super(DictWrapper, self).__init__()
        # Overriding __len__ is not enough to convince PyDict_GET_SIZE()
        if context:
            self['1'] = True
        # The only part of the dict API that json.JSONEncoder is _actually_
        # interested in.
        self.items = context._mapping.items


ENCODERS = {
    datetime.date: datetime_encode,
    datetime.datetime: datetime_encode,
    decimal.Decimal: decimal_encode,
    sqlalchemy.engine.Row: DictWrapper,
}


def encode(o):
    for klass, encoder in ENCODERS.items():
        if isinstance(o, klass):
            return encoder(o)
    return json._default_encoder._default_orig(o)


json._default_encoder._default_orig = json._default_encoder.default
json._default_encoder.default = encode
