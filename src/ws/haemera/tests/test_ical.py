from ws.haemera.action import Action
from ws.haemera.ical import _instantiate_recurring as instantiate
import pendulum
import transaction


def test_one(db, clock):
    template = Action()
    template.subject = 'test'
    template.rrule = 'FREQ=WEEKLY;BYDAY=SU'
    template.timestamp = pendulum.date(2019, 1, 1)
    db.add(template)
    transaction.commit()
    tpl = template.id

    clock(pendulum.parse('2019-01-04'))
    instantiate(template)
    transaction.commit()
    template = Action.find_by_id(tpl)

    assert Action.query().filter_by(status='scheduled').count() == 1
    assert template.latest_instance.strftime('%Y-%m-%d') == '2019-01-06'

    clock(pendulum.parse('2019-01-05'))
    instantiate(template)
    transaction.commit()
    template = Action.find_by_id(tpl)
    assert Action.query().filter_by(status='scheduled').count() == 1
    assert template.latest_instance.strftime('%Y-%m-%d') == '2019-01-06'

    clock(pendulum.parse('2019-01-06'))
    instantiate(template)
    transaction.commit()
    template = Action.find_by_id(tpl)
    assert Action.query().filter_by(status='scheduled').count() == 2
    assert template.latest_instance.strftime('%Y-%m-%d') == '2019-01-13'

    clock(pendulum.parse('2019-01-07'))
    instantiate(template)
    transaction.commit()
    template = Action.find_by_id(tpl)
    assert Action.query().filter_by(status='scheduled').count() == 2
    assert template.latest_instance.strftime('%Y-%m-%d') == '2019-01-13'
