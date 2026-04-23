# novelcast/utils/files.py

import re

class FileUtils:

    def safe(self, name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        return re.sub(r'\s+', '_', name).strip('_')