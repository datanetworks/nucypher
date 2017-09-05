import appdirs
import lmdb
import os.path

CONFIG_APPNAME = 'nucypher-kms'
DB_NAME = 'rekeys-db'


class DB(object):
    def __init__(self, path=None):
        self.path = path or os.path.join(
                appdirs.user_data_dir(CONFIG_APPNAME), DB_NAME)
        db_dir = os.path.dirname(self.path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)

        self.db = lmdb.open(self.path)
        # XXX removal when expired? Indexing by time?

    def __setitem__(self, key, value):
        with self.db.begin(write=True) as tx:
            tx.put(key, value)

    def __getitem__(self, key):
        with self.db.begin(write=False) as tx:
            return tx.get(key)

    def close(self):
        self.db.close()