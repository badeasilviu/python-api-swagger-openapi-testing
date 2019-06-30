class ContentHelper:
    def __value_or_default__(self, key, content, default_value=""):
        try:
            return content[key]
        except (KeyError, TypeError) as e:
            return default_value

    def __keys_or_default__(self, key, content, default_value=""):
        try:
            return content[key].keys()
        except (KeyError, TypeError) as e:
            return default_value

    def __get_iterator__(self, data):
        if not isinstance(data, (tuple, list)):
            return (data,)
        else:
            return data