from sqlalchemy import Column, Integer, String, Boolean, Text, ForeignKey, TIMESTAMP, JSON, CheckConstraint, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(100), nullable=False)
    email = Column(String(50))
    google_id = Column(Text)
    github_id = Column(Text)
    profile_photo = Column(Text)
    bio = Column(Text)
    created_date = Column(TIMESTAMP, server_default='now()')
    updated_date = Column(TIMESTAMP)
    is_active = Column(Boolean, default=False)
    verification_token = Column(Text)
    tsv = Column(Text)  # tsvector
    reset_password_token = Column(Text)
    reset_password_expires = Column(TIMESTAMP)

class Activity(Base):
    __tablename__ = 'activity'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    target_id = Column(Integer, nullable=False)
    primary_text = Column(String(255))
    activity_type = Column(String(50), CheckConstraint("activity_type IN ('passive', 'active')"), nullable=False)
    target_type = Column(String(50), CheckConstraint("target_type IN ('favorite', 'game', 'game_session', 'playlist', 'review', 'comment', 'share')"), nullable=False)
    timestamp = Column(TIMESTAMP, server_default='now()')

class Comment(Base):
    __tablename__ = 'comments'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    game_id = Column(Integer)
    parent_comment_id = Column(Integer, ForeignKey('comments.id'))
    comment_text = Column(Text)
    tsv = Column(Text)  # tsvector
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP)

class Favorite(Base):
    __tablename__ = 'favorites'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    game_id = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP, server_default='now()')
    __table_args__ = (UniqueConstraint('user_id', 'game_id', name='favorites_user_id_game_id_key'),)

class Follow(Base):
    __tablename__ = 'follows'
    follow_id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    following_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    timestamp = Column(TIMESTAMP, server_default='now()')

class GamePlaylist(Base):
    __tablename__ = 'game_playlist'
    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.id', ondelete='CASCADE'), nullable=False)
    playlist_id = Column(Integer, ForeignKey('playlist.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')
    item_order = Column(Integer)

class GameSession(Base):
    __tablename__ = 'game_session'
    game_session_id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')
    session_total_time = Column(Text)  # interval
    session_total_score = Column(Integer)

class GameTag(Base):
    __tablename__ = 'game_tags'
    game_id = Column(Integer, ForeignKey('games.id'), primary_key=True)
    tag_id = Column(Integer, ForeignKey('tags.id'), primary_key=True)

class GameUserActivity(Base):
    __tablename__ = 'game_user_activity'
    game_user_activity_id = Column(Integer, primary_key=True, index=True)
    game_session_id = Column(Integer, ForeignKey('game_session.game_session_id'), nullable=False)
    action = Column(String, nullable=False)  # Replace with an appropriate type for game_action
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')

class Game(Base):
    __tablename__ = 'games'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    title = Column(Text)
    description = Column(Text)
    published = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')
    thumbnail = Column(Text)
    tsv = Column(Text)  # tsvector

class Playlist(Base):
    __tablename__ = 'playlist'
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text)
    description = Column(Text)
    is_public = Column(Boolean, default=False)
    is_category = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')
    tsv = Column(Text)  # tsvector
    thumbnail = Column(Text)

class Review(Base):
    __tablename__ = 'reviews'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    game_id = Column(Integer, nullable=False)
    rating = Column(Integer, CheckConstraint('rating >= 0 AND rating <= 5'), nullable=False)
    review_text = Column(Text)
    __table_args__ = (UniqueConstraint('user_id', 'game_id', name='reviews_user_id_game_id_key'),)

class Tag(Base):
    __tablename__ = 'tags'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False, unique=True)

class UserActivityFeed(Base):
    __tablename__ = 'user_activity_feed'
    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey('activity.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    viewed = Column(Boolean, default=False)

class UserPlaylist(Base):
    __tablename__ = 'user_playlist'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    playlist_id = Column(Integer, ForeignKey('playlist.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')

class UserSetting(Base):
    __tablename__ = 'user_settings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_date = Column(TIMESTAMP, server_default='now()')
    updated_date = Column(TIMESTAMP)
    hide_pop_up_info = Column(Boolean, default=False)
    dark_mode = Column(Boolean, default=False)
    hide_pop_up_info_home = Column(Boolean, default=False)
    hide_pop_up_info_games = Column(Boolean, default=False)
    hide_pop_up_info_editor = Column(Boolean, default=False)

class DynamicItem(Base):
    __tablename__ = 'dynamic_item'
    item_id = Column(Integer, primary_key=True, index=True)
    item_type = Column(String(50), nullable=False)  # e.g., 'recommendation', 'activity', 'ad'
    content = Column(JSON, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False)

    priorities = relationship("DynamicItemPriority", back_populates="dynamic_item")
    feeds = relationship("DynamicUserFeed", back_populates="dynamic_item")

class DynamicItemPriority(Base):
    __tablename__ = 'dynamic_item_priority'
    item_id = Column(Integer, ForeignKey('dynamic_item.item_id'), primary_key=True)
    user_id = Column(Integer, primary_key=True)
    priority_score = Column(Integer, nullable=False)
    
    dynamic_item = relationship("DynamicItem", back_populates="priorities")

class DynamicUserFeed(Base):
    __tablename__ = 'dynamic_user_feed'
    user_id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey('dynamic_item.item_id'), primary_key=True)
    feed_timestamp = Column(TIMESTAMP, nullable=False)
    
    dynamic_item = relationship("DynamicItem", back_populates="feeds")

class UserPersona(Base):
    __tablename__ = 'user_personas'
    user_id = Column(Integer, primary_key=True)
    persona = Column(JSON, nullable=False)
    last_updated = Column(TIMESTAMP, nullable=False)

class PlaylistSession(Base):
    __tablename__ = "playlist_session"
    session_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    playlist_id = Column(Integer, index=True)
    completed = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP)
    updated_at = Column(TIMESTAMP)

class PlaylistUserActivity(Base):
    __tablename__ = 'playlist_user_activity'
    playlist_user_activity_id = Column(Integer, primary_key=True, index=True)
    playlist_session_id = Column(Integer, ForeignKey('playlist_session.session_id'), nullable=False)
    action = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default='now()')
    updated_at = Column(TIMESTAMP, server_default='now()')

