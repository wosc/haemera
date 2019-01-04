# Taken from <https://bitbucket.org/gocept/risclog.sqlalchemy
#   /src/tip/src/risclog/sqlalchemy/serializer.py>
import datetime
import decimal
import json


def datetime_encode(o, request=None):
    return o.isoformat()


def decimal_encode(o, request=None):
    return str(o)


ENCODERS = {
    datetime.date: datetime_encode,
    datetime.datetime: datetime_encode,
    decimal.Decimal: decimal_encode
}


def encode(o):
    for klass, encoder in ENCODERS.items():
        if isinstance(o, klass):
            return encoder(o)
    return json._default_encoder._default_orig(o)


json._default_encoder._default_orig = json._default_encoder.default
json._default_encoder.default = encode
