class DictLike:
    def __getitem__(self, item):
        if not hasattr(self, item):
            raise KeyError(item)
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def get(self, key, default=None):
        return getattr(self, key, default)