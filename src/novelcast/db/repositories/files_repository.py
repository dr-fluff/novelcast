class FilesRepository:
    def __init__(self, db):
        self.db = db

    def get_by_id(self, file_id: int):
        return self.db.fetchone(
            "SELECT * FROM files WHERE id = ?",
            (file_id,),
        )

    def update_metadata(self, file_id: int, size: int):
        return self.db.execute(
            "UPDATE files SET size = ? WHERE id = ?",
            (size, file_id),
        )