
class Authenticator:

    def __init__(self, token=None, allow_all=False):

        if not allow_all and token is None:
            raise RuntimeError("Need a token")

        if not allow_all and token == "":
            raise RuntimeError("Need a token")

        self.token = token
        self.allow_all = allow_all

    def permitted(self, token, roles):

        if self.allow_all: return True

        if self.token != token: return False

        return True

