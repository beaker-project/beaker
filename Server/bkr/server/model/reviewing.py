
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, Unicode, DateTime
from sqlalchemy.orm import relationship, validates
from .base import DeclarativeMappedObject
from .identity import User
from .scheduler import RecipeSet

log = logging.getLogger(__name__)

class RecipeSetComment(DeclarativeMappedObject):

    __tablename__ = 'recipe_set_comment'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    recipe_set_id = Column(Integer, ForeignKey('recipe_set.id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    recipeset = relationship(RecipeSet, back_populates='comments')
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    user = relationship(User)
    comment = Column(Unicode(4000), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __json__(self):
        return {
            'id': self.id,
            'user': self.user,
            'comment': self.comment,
            'created': self.created,
        }

    @validates('comment')
    def validate_comment(self, key, value):
        if not value:
            raise ValueError('Comment text cannot be empty')
        if value.isspace():
            raise ValueError('Comment text cannot consist of only whitespace')
        return value
