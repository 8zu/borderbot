class ChannelRegistry(object):
    def __init__(self, channels):
        self._data = set(tuple(ch) for ch in channels)

    def __contains__(self, _id):
        return sum(1 for _ in (filter(lambda ch: ch[0] == _id, self._data))) > 0

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def add(self, _id, server, name):
        self._data.add((_id, name, server))

    def remove(self, _id):
        self._data = set(filter(lambda ch: ch[0] != _id, self._data))

    def difference_update(self, to_be_removed):
        for ch in to_be_removed:
            self.remove(ch)

    def save(self, cache):
        cache.save('channels.json', list(self._data))
