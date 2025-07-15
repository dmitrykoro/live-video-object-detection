import uuid

from datetime import datetime, UTC
from email.policy import default

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import declarative_base, relationship, mapped_column, Mapped


Base = declarative_base()


class StreamSubscription(Base):
    __tablename__ = 'stream_subscription'

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(200))
    user_id = Column(String(36), ForeignKey('user.id'), nullable=False)
    is_deleted = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    provide_notification = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now(UTC))
    frame_fetch_frequency = Column(Integer, nullable=False)
    last_frame_fetched_at = Column(DateTime, nullable=True)
    target_bird_species = Column(Text, nullable=True)
    misc_info = Column(Text, nullable=True)
    target_timestamp_ms = Column(Integer, default=1)

    user = relationship("User", back_populates="subscriptions")
    recognition_history = relationship("RecognitionEntry", back_populates="stream_subscription")


class User(Base):
    __tablename__ = 'user'

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(150), unique=True, nullable=False)
    email = Column(String(254), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.now(UTC))
    is_sns_subscribed = Column(Boolean, default=False)
    sns_topic_arn = Column(String(255), unique=True, nullable=True)

    subscriptions = relationship("StreamSubscription", back_populates="user")


class RecognitionEntry(Base):
    __tablename__ = "recognition_entry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    stream_subscription_id = Column(Integer, ForeignKey("stream_subscription.id", ondelete="CASCADE"), nullable=False)
    earth_timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    stream_timestamp = Column(DateTime, default=lambda: datetime.now(UTC), nullable=False)
    recognized_specie_name = Column(String(255), nullable=False)
    recognized_specie_img_url = Column(String(200), nullable=False)

    stream_subscription = relationship("StreamSubscription", back_populates="recognition_history")
