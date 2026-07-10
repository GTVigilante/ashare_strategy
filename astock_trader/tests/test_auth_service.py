import unittest

from services.auth_service import SessionStore, password_matches


class AuthServiceTests(unittest.TestCase):
    def test_password_comparison(self):
        self.assertTrue(password_matches("correct horse", "correct horse"))
        self.assertFalse(password_matches("wrong", "correct horse"))
        self.assertFalse(password_matches("anything", ""))

    def test_session_lifecycle(self):
        store = SessionStore(ttl_seconds=60)
        token, expires_in = store.create()
        self.assertEqual(expires_in, 60)
        self.assertTrue(store.validate(token))
        store.revoke(token)
        self.assertFalse(store.validate(token))

    def test_expired_session_is_rejected(self):
        store = SessionStore(ttl_seconds=-1)
        token, _ = store.create()
        self.assertFalse(store.validate(token))


if __name__ == "__main__":
    unittest.main()
