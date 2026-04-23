import logging

from novelcast.db.database import Database
from novelcast.db.query_manager import QueryManager

from novelcast.db.repositories.stories_repository import StoriesRepository
from novelcast.db.repositories.users_repository import UsersRepository
from novelcast.db.repositories.files_repository import FilesRepository

from novelcast.services.story_service import StoryService
from novelcast.services.user_service import UserService
from novelcast.services.auth_service import AuthService
from novelcast.services.file_service import FileService
from novelcast.services.page_service import PageService


logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self):
        try:
            logger.info("Initializing database...")
            self.db = Database()
            self.db.init_schema()

            logger.info("Initializing QueryManager...")
            self.qm = QueryManager(self.db)

            
            # repositories
            stories_repo = StoriesRepository(self.db)
            users_repo = UsersRepository(self.db)
            files_repo = FilesRepository(self.db)

            # services
            self.stories = StoryService(stories_repo)
            self.users = UserService(users_repo)
            self.auth = AuthService(users_repo)
            self.files = FileService(files_repo)

            self.pages = PageService(stories_repo)

            logger.info("AppContext ready")

        except Exception:
            logger.exception("Fatal error in AppContext")
            raise