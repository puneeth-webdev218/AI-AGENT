from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Text, Float, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Result(Base):
    __tablename__ = 'results'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey('students.id', ondelete='SET NULL'), nullable=True, index=True)
    student_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    usn: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    subject_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(32), nullable=True)
    grade_points: Mapped[float | None] = mapped_column(Float, nullable=True)
    sgpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(32), nullable=False, default='partial')
    validation_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    document = relationship('Document', back_populates='results')
    student = relationship('Student', back_populates='results')
