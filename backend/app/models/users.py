"""SQLAlchemy 2 models for user accounts."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy import Boolean, Column, DateTime, String, Text

from sqlalchemy.dialects.postgresql import CITEXT
from sqlalchemy.types import Integer

from .base import Base