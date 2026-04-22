# novelcast/core/context.py

from novelcast.db.database import Database
from novelcast.db.query_manager import QueryManager

from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService
from novelcast.services.file_service import FileService
from novelcast.services.page_service import PageService
from novelcast.services.subscription_service import SubscriptionService


class AppContext:
    def __init__(self):
        self.db = Database()
        self.qm = QueryManager(self.db)

        # services (wired once here)
        self.users = UserService(self.qm)
        self.auth = AuthService(self.qm)
        self.files = FileService(self.qm)
        self.pages = PageService(self.qm)
        self.subscriptions = SubscriptionService(self.qm)