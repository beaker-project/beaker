
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

from datetime import datetime
from sqlalchemy import Column, Integer, Unicode
from sqlalchemy.sql import and_
from sqlalchemy.orm import class_mapper, relationship, dynamic_loader
from turbogears.database import session
from bkr.server.bexceptions import BeakerException, BX, \
        StaleTaskStatusException, \
        InsufficientSystemPermissions, StaleSystemUserException, \
        StaleCommandStatusException, NoChangeException
from bkr.server.installopts import InstallOptions

from .base import DeclarativeMappedObject, MappedObject
from .migration import DataMigration
from .types import (TaskStatus, CommandStatus, TaskResult, TaskPriority,
        SystemStatus, SystemType, ReleaseAction, ImageType, ResourceType,
        RecipeVirtStatus, SystemPermission, UUID, MACAddress, IPAddress,
        GroupMembershipType, SystemSchedulerStatus)
from .activity import Activity, ActivityMixin
from .config import ConfigItem
from .identity import (User, Group, Permission, SSHPubKey,
        UserGroup, ExcludedUserGroup, UserActivity, GroupActivity)
from .lab import LabController, LabControllerActivity
from .distrolibrary import (Arch, KernelType, OSMajor, OSVersion,
        OSMajorInstallOptions, Distro, DistroTree, DistroTreeImage,
        DistroTreeRepo, DistroTag, DistroActivity, DistroTreeActivity,
        LabControllerDistroTree, install_options_for_distro)
from .tasklibrary import (Task, TaskLibrary, TaskPackage, TaskType,
        TaskBugzilla, TaskPropertyNeeded)
from .inventory import (System, SystemStatusDuration, SystemCc, Hypervisor,
        Cpu, CpuFlag, Disk, Device, DeviceClass, Numa, Power, PowerType, Note,
        Key, Key_Value_String, Key_Value_Int, Provision, ProvisionFamily,
        ProvisionFamilyUpdate, ExcludeOSMajor, ExcludeOSVersion, LabInfo,
        SystemAccessPolicy, SystemAccessPolicyRule, Reservation,
        SystemActivity, Command, SystemPool, SystemPoolActivity)
from .installation import Installation, RenderedKickstart
from .scheduler import (Watchdog, TaskBase, Job, RecipeSet, Recipe,
        RecipeTaskResult, MachineRecipe, GuestRecipe, RecipeTask, Log,
        LogRecipe, LogRecipeTask, LogRecipeTaskResult, JobCc, RecipeResource,
        SystemResource, GuestResource, VirtResource, RetentionTag,
        Product, RecipeActivity, RecipeSetActivity, RecipeRepo,
        RecipeKSAppend, RecipeTaskParam, JobActivity, RecipeReservationRequest,
        RecipeReservationCondition)
from .reviewing import RecipeSetComment, RecipeReviewedState, RecipeTaskComment,\
    RecipeTaskResultComment
from .openstack import OpenStackRegion

# Delayed property definitions due to circular dependencies
class_mapper(Group).add_properties({
    'dyn_owners': dynamic_loader(User, secondary=UserGroup.__table__, viewonly=True,
        primaryjoin=and_(UserGroup.group_id == Group.group_id,
                         UserGroup.is_owner == True)),
})
class_mapper(LabController).add_property('dyn_systems', dynamic_loader(System))
class_mapper(System).add_properties({
    # The relationship to 'recipe' is complicated
    # by the polymorphism of SystemResource :-(
    'recipes': relationship(Recipe, viewonly=True,
        secondary=RecipeResource.__table__.join(SystemResource.__table__),
        secondaryjoin=and_(SystemResource.__table__.c.id == RecipeResource.id,
            RecipeResource.recipe_id == Recipe.id)),
    'dyn_recipes': dynamic_loader(Recipe,
        secondary=RecipeResource.__table__.join(SystemResource.__table__),
        secondaryjoin=and_(SystemResource.__table__.c.id == RecipeResource.id,
            RecipeResource.recipe_id == Recipe.id)),
})
class_mapper(Reservation).add_properties({
    # The relationship to 'recipe' is complicated
    # by the polymorphism of SystemResource :-(
    'recipe': relationship(Recipe, uselist=False, viewonly=True,
        secondary=RecipeResource.__table__.join(SystemResource.__table__),
        secondaryjoin=and_(SystemResource.__table__.c.id == RecipeResource.id,
            RecipeResource.recipe_id == Recipe.id)),
})

## Static list of device_classes -- used by master.kid
# (This is populated by bkr.server.wsgi:init before the first request.)
device_classes = []
