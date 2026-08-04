from novelcast.engine.engine_patreon import PatreonEngine


class DummySettingsService:
    def __init__(self, value):
        self.value = value

    def get_secret(self, key):
        return self.value

    def _decrypt_secret_value(self, value):
        if value == "ncsec:v1:bad":
            raise ValueError("bad secret")
        return value


def test_cookie_returns_plain_value():
    engine = PatreonEngine(settings_repo=None, settings_service=DummySettingsService("session-123"))
    assert engine._cookie() == "session-123"


def test_cookie_falls_back_when_encrypted_secret_cannot_be_decrypted():
    engine = PatreonEngine(settings_repo=None, settings_service=DummySettingsService("ncsec:v1:bad"))
    assert engine._cookie() == "ncsec:v1:bad"
