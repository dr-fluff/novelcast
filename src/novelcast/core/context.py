from novelcast.db.database import Database
from novelcast.db. query_manager import QueryManager

class AppContext:
    def __init__(self):
        self.db = None
        self.qm = None

    def init(self):
        self.db = Database()
        self.qm = QueryManager(self.db)