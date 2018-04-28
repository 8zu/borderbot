import json
from copy import deepcopy
from datetime import datetime

import pytz
from api import APIEndpoint

credits = "データー提供： @imas_ml_td"

# [theater-gate] website url
event_url = "https://otomestorm.anzu.work/events"

event_api = APIEndpoint(event_url)

# border data api url without defined event code
json_api_url = "https://otomestorm.anzu .work/events/{}/rankings/event_point?special_token={}"

# helper
Event_type_with_border = [3, 4]

Japan_TZ = pytz.timezone('Japan')
format_string = "%Y-%m-%dT%H:%M:%S"
format_string_simple = "%Y-%m-%d %H:%M"


def first(iterator):
    try:
        return next(iterator)
    except StopIteration:
        return None

def get_japan_time(time=None):
    if time:
        return Japan_TZ.localize(datetime.strptime(time, format_string))
    else:
        return datetime.now(Japan_TZ)


class EventRecord(object):
    def __init__(self, event_code, name, starts, ends, has_border):
        self.id = event_code
        self.name = name
        self.starts = get_japan_time(starts)
        self.ends = get_japan_time(ends)
        now = get_japan_time()
        self.is_active = self.starts < now < self.ends
        self.has_border = has_border

    def __repr__(self):
        starts = self.starts.strftime(format_string)
        ends = self.ends.strftime(format_string)
        active = "Ongoing" if self.is_active else "Inactive"
        has_border = "Has borders" if self.has_border else "Doesn't have borders"
        return f"Event #{self.id}: {self.name}\nstarts {starts}\nends {ends}\n{active}\n{has_border}"

    def fetch_border(self, secret_token):
        if not self.has_border:
            raise ValueError("This event does not have border")
        res = event_api[str(self.id)].rankings.event_point.get_json(special_token=secret_token)
        if res.ok:
            if not res.val['status']:
                raise IOError("Error 404: event not found")
            latest_border = res.val['data']['logs'][-1]
            latest_border['metadata'] = {'name': self.name,
                                         'id': self.id,
                                         'starts': self.starts,
                                         'ends': self.ends}
            return latest_border
        else:
            raise IOError(str(res.exn))


def get_event_metadata(event_code=None):
    """
    :return: packaged event info including event title, start time and end time.
    """
    res = event_api.get_json()
    if res.ok and res.val['status']:
        evs = res.val['data']
        if not event_code:
            ev = first(filter(lambda ev: ev['event_type'] in Event_type_with_border, \
                            reversed(evs)))
        else:
            ev = first(filter(lambda ev: ev['event_id'] == event_code, evs))
        if not ev:
            raise IOError('Could not find event with border')
        return EventRecord(ev['event_id'],
                           ev['event_name'],
                           ev['schedule']['begin_at'],
                           ev['schedule']['end_at'],
                           ev['event_type'] in Event_type_with_border)
    elif res.ok:
        raise IOError("Error 404. Event list not found")
    else:
        raise IOError(str(res.))


def get_datetime(s):
    if type(s) is str:
        return get_japan_time(s)
    else:
        return s


def get_str(d):
    if type(d) is str:
        return d
    else:
        return d.strftime(format_string_simple)


def format_with(border, prev=None):
    starts = get_datetime(border['metadata']['starts'])
    ends = get_datetime(border['metadata']['ends'])
    now = get_japan_time(border['datetime'])
    delta = ends - now
    borders = {int(k): v for k, v in border['borders'].items()}
    if prev:
        prev = {int(k): v for k, v in prev['borders'].items()}
    starts = get_str(starts)
    ends = get_str(ends)
    timeleft = f'{starts}～{ends}, '
    if delta.days >= 0:
        timeleft += f'あと {delta.days} 日 {delta.seconds // 3600} 時間'
    else:
        timeleft += 'イベントが終わりました'
        prev = None

    lines = ['```',
             border['metadata']['name'],
             timeleft,
             credits,
             '',
             now.strftime(format_string_simple)]
    maxlen = len(str(max(borders.keys()))) + 8 + len('{:,}'.format(max(borders.values())))
    for n, score in sorted(borders.items()):
        offset = len(str(n)) + 8
        line = f"{n}位：  {score:>{maxlen-offset},}"
        if prev:
            diff = score - prev[n]
            line += f" (+{diff:,})"
        lines.append(line)
    lines.append('```')
    return '\n'.join(lines)


def serialize(border):
    bd2 = deepcopy(border)
    bd2['metadata']['starts'] = border['metadata']['starts'].strftime(format_string)
    bd2['metadata']['ends'] = border['metadata']['ends'].strftime(format_string)
    return bd2
