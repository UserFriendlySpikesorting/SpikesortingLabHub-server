import os
import sys
import sqlite3
from pathlib import Path

from passlib.hash import sha512_crypt

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist

# Absolute path to the NAS database, overridable via environment variable
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
NAS_DB_PATH = os.environ.get("NAS_DB_PATH", str(_PROJECT_ROOT / "NAS_Database" / "freenas-v1.db"))


class FreeNASBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        try:
            conn = sqlite3.connect(NAS_DB_PATH)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT bsdusr_username, bsdusr_unixhash "
                "FROM account_bsdusers "
                "WHERE bsdusr_username=? OR bsdusr_email=?",
                (username, username),
            )
            result = cursor.fetchone()
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"NAS database error during authentication: {e} | path={NAS_DB_PATH}", file=sys.stderr)
            return None

        if result is None:
            return None

        db_username, db_password_hash = result
        if not sha512_crypt.verify(password, db_password_hash):
            return None

        try:
            user = User.objects.get(username=db_username)
        except ObjectDoesNotExist:
            user = User(username=db_username)
            user.set_unusable_password()
            user.save()

        return user

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except ObjectDoesNotExist:
            return None
