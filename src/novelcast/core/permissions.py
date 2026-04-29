from fastapi import Depends, HTTPException
from novelcast.auth.dependencies import get_current_user
from novelcast.api.deps import require_user

class PermissionManager:
    def __init__(self, qm):
        self.qm = qm

    def get_user_groups(self, user_id):
        rows = self.qm.fetchall(
            "SELECT group_id FROM user_groups WHERE user_id = ?",
            (user_id,)
        )
        return {r["group_id"] for r in rows}

    def get_file_groups(self, file_id):
        rows = self.qm.fetchall(
            "SELECT group_id FROM file_permissions WHERE file_id = ?",
            (file_id,)
        )
        return {r["group_id"] for r in rows}

    def can_access_file(self, user_id, file_id):
        user_groups = self.get_user_groups(user_id)
        file_groups = self.get_file_groups(file_id)

        user = self.qm.fetchone("users.get_by_id", (user_id,))

        if user and user.get("is_root"):
            return True

        return bool(user_groups & file_groups)


def require_admin(user=Depends(require_user)):
    if not user or not user.get("is_root"):
        raise HTTPException(status_code=403, detail="Admins only")
    return user