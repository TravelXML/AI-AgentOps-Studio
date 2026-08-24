"""Local encrypted secrets store (spec section 40). FlowSpec, logs, and traces only ever see a
`secret_id` reference - raw values are decrypted exactly once, at the point a provider SDK call
needs an API key, and never returned through any API response."""

from __future__ import annotations

import base64
import hashlib
import uuid

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentq_api.config import Settings
from agentq_api.db.models import Secret


def _fernet_for(app_secret: str) -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(app_secret.encode()).digest())
    return Fernet(key)


class SecretsService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._fernet = _fernet_for(settings.app_secret)

    async def create(self, workspace_id: uuid.UUID, name: str, value: str) -> Secret:
        secret = Secret(
            workspace_id=workspace_id,
            name=name,
            ciphertext=self._fernet.encrypt(value.encode()),
        )
        self._session.add(secret)
        await self._session.flush()
        return secret

    async def resolve(self, secret_id: uuid.UUID | str | None) -> str | None:
        if secret_id is None:
            return None
        result = await self._session.execute(select(Secret).where(Secret.id == secret_id))
        secret = result.scalar_one_or_none()
        if secret is None:
            return None
        return self._fernet.decrypt(secret.ciphertext).decode()
