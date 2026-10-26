"""SQLAlchemy 2 models for OpenSeat backend."""

from __future__ import annotations

from sqlalchemy import Boolean, Column, DateTime, Float, func
from sqlalchemy.dialects.postgresql import INET, CIDR, CITEXT
from sqlalchemy.types import Integer, String, SmallInteger

from .base import Base