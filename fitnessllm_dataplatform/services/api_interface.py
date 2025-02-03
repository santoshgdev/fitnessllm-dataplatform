from abc import abstractmethod


class APIInterface:
    def __init__(self):
        pass

    @abstractmethod
    def refresh_access_token_at_expiration(self):
        pass

    @abstractmethod
    def write_refreshed_access_token_to_redis(self):
        pass