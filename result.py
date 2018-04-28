class Result(object):
    pass

class Ok(Result):
    def __init__(self, val):
        self.val = val

    @property
    def ok(self):
        return True

    def map(self, f):
        return Ok(f(self.val))

    def or_else(self, _):
        return self.val

class Err(Result):
    def  __init__(self, exn):
        self.exn = exn

    @property
    def ok(self):
        return False

    def map(self, f):
        return self

    def or_else(self, alt):
        return alt
