import json
from copy import deepcopy
from datetime import datetime

import pytz
import requests as req

# [theater-gate] website url
event_url = "https://otomestorm.anzu.work/events"

# border data api url without defined event code
json_api_url = "https://otomestorm.anzu.work/events/{}/rankings/event_point"

# helper
Event_type_with_border = [3, 4]

Japan_TZ = pytz.timezone('Japan')
format_string = "%Y-%m-%dT%H:%M:%S"
format_string_simple = "%Y-%m-%d %H:%M"


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

    def fetch_border(self):
        if not self.has_border:
            raise ValueError("This event does not have border")
        actual_api_url = json_api_url.format(self.id)
        res = req.get(actual_api_url)
        if res.status_code == 200:
            obj = json.loads(res.text)
            if not obj['status']:
                raise IOError("Error 404: event not found")
            latest_border = obj['data']['logs'][-1]
            latest_border['metadata'] = {'name': self.name,
                                         'id': self.id,
                                         'starts': self.starts,
                                         'ends': self.ends}
            return latest_border
        else:
            raise IOError(f"Error {res.status_code}")


def get_latest_event_metadata():
    """
    :return: packaged event info including event title, start time and end time.
    """
    res = req.get(event_url)
    if res.status_code == 200:
        obj = json.loads(res.text)
        if not obj['status']:
            raise IOError("Error 404. Event list not found")
        evs = obj['data']
        ev = None
        for ev in reversed(evs):
            if ev['event_type'] in Event_type_with_border:
                break
        if not ev:
            raise IOError('Could not find event with border')
        return EventRecord(ev['event_id'],
                           ev['event_name'],
                           ev['schedule']['begin_at'],
                           ev['schedule']['end_at'],
                           ev['event_type'] in Event_type_with_border)
    else:
        raise IOError(f"Error {res.status_code}")


def get_past_event_border(event_code):
    """
    Get past event border.
    :param event_code: event code
    :return: final border result
    """
    actual_api_url = json_api_url.format(event_code)
    res = req.get(actual_api_url)
    if res.status_code == 200:
        obj = json.loads(res.text)
        if not obj['status']:
            raise IOError("Error 404: event not found")
        latest_border = obj['data']['logs'][-1]
        er = get_past_event_metadata(event_code)
        latest_border['metadata'] = {'name': er.name,
                                     'id': er.id,
                                     'starts': er.starts,
                                     'ends': er.ends}
        return latest_border
    else:
        raise IOError(f"Error {res.status_code}")


def get_past_event_metadata(event_code):
    res = req.get(event_url)
    if res.status_code == 200:
        obj = json.loads(res.text)
        if not obj['status']:
            raise IOError("Error 404. Event list not found")
        evs = obj['data']
        ev = None
        for ev in reversed(evs):
            if int(ev['event_id']) is int(event_code):
                break
        if not ev:
            raise IOError('Could not find event with border')
        return EventRecord(ev['event_id'],
                           ev['event_name'],
                           ev['schedule']['begin_at'],
                           ev['schedule']['end_at'],
                           ev['event_type'] in Event_type_with_border)


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
    if delta.days > 0:
        timeleft += f'あと {delta.days} 日 {delta.seconds // 3600} 時間'
    else:
        timeleft += 'イベントが終わりました'

    lines = ['```',
             border['metadata']['name'],
             timeleft,
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
