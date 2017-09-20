
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

import logging
from datetime import datetime
from sqlalchemy import Column, ForeignKey, Integer, Unicode, DateTime, Boolean
from sqlalchemy.orm import relationship, validates
from .base import DeclarativeMappedObject
from .identity import User
from .scheduler import RecipeSet, Recipe, RecipeTask, RecipeTaskResult

log = logging.getLogger(__name__)

class CommentBase(DeclarativeMappedObject):
    __abstract__ = True

    # Defined on subclasses
    id = 0
    user = None
    comment = u''
    created = datetime.utcnow()

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


class RecipeSetComment(CommentBase):

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

class RecipeTaskComment(CommentBase):

    __tablename__ = 'recipe_task_comment'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    recipe_task_id = Column(Integer, ForeignKey('recipe_task.id',
            name='recipe_task_comment_recipe_task_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    recipetask = relationship(RecipeTask, back_populates='comments')
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            name='recipe_task_comment_user_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    user = relationship(User)
    comment = Column(Unicode(4000), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)

class RecipeTaskResultComment(CommentBase):

    __tablename__ = 'recipe_task_result_comment'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    id = Column(Integer, autoincrement=True, primary_key=True)
    recipe_task_result_id = Column(Integer, ForeignKey('recipe_task_result.id',
            name='recipe_task_result_comment_recipe_task_result_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    recipetaskresult = relationship(RecipeTaskResult, back_populates='comments')
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            name='recipe_task_result_comment_user_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    user = relationship(User)
    comment = Column(Unicode(4000), nullable=False)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)

class RecipeReviewedState(DeclarativeMappedObject):

    """
    This is a per-user, per-recipe boolean flag meaning "have I reviewed this 
    recipe yet?" It's intended to be a totally optional way for users to keep 
    track of which parts of their job results they have reviewed.
    """

    __tablename__ = 'recipe_reviewed_state'
    __table_args__ = {'mysql_engine': 'InnoDB'}
    recipe_id = Column(Integer, ForeignKey('recipe.id',
            name='recipe_reviewed_state_recipe_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    recipe = relationship(Recipe)
    user_id = Column(Integer, ForeignKey('tg_user.user_id',
            name='recipe_reviewed_state_user_id_fk',
            onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
    user = relationship(User)
    reviewed = Column(Boolean, nullable=False, default=True)

    @classmethod
    def lazy_create(cls, recipe, user, reviewed):
        return super(RecipeReviewedState, cls).lazy_create(
                recipe_id=recipe.id, user_id=user.user_id,
                _extra_attrs=dict(reviewed=reviewed))
