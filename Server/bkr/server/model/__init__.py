
from datetime import datetime
from sqlalchemy import Column, Integer, Unicode
from sqlalchemy.sql import and_
from sqlalchemy.orm import class_mapper, relation, dynamic_loader
from turbogears.database import session
from bkr.server.bexceptions import BeakerException, BX, \
        VMCreationFailedException, StaleTaskStatusException, \
        InsufficientSystemPermissions, StaleSystemUserException, \
        StaleCommandStatusException, NoChangeException
from bkr.server.installopts import InstallOptions

from .base import DeclarativeMappedObject, MappedObject
from .types import (TaskStatus, CommandStatus, TaskResult, TaskPriority,
        SystemStatus, SystemType, ReleaseAction, ImageType, ResourceType,
        RecipeVirtStatus, SystemPermission, UUID, MACAddress)
from .activity import Activity, ActivityMixin, activity_table
from .config import ConfigItem
from .identity import (User, Group, Permission, SSHPubKey, SystemGroup,
        UserGroup, UserActivity, GroupActivity, users_table)
from .lab import LabController, LabControllerActivity, lab_controller_table
from .distrolibrary import (Arch, KernelType, OSMajor, OSVersion,
        OSMajorInstallOptions, Distro, DistroTree, DistroTreeImage,
        DistroTreeRepo, DistroTag, DistroActivity, DistroTreeActivity,
        LabControllerDistroTree, kernel_type_table, arch_table,
        osmajor_table, distro_table, distro_tree_table,
        distro_tree_lab_controller_map)
from .tasklibrary import (Task, TaskExcludeArch, TaskExcludeOSMajor,
        TaskLibrary, TaskPackage, TaskType, TaskBugzilla, TaskPropertyNeeded,
        task_table, task_exclude_osmajor_table, task_exclude_arch_table)
from .inventory import (System, SystemStatusDuration, SystemCc, Hypervisor,
        Cpu, CpuFlag, Disk, Device, DeviceClass, Numa, Power, PowerType, Note,
        Key, Key_Value_String, Key_Value_Int, Provision, ProvisionFamily,
        ProvisionFamilyUpdate, ExcludeOSMajor, ExcludeOSVersion, LabInfo,
        SystemAccessPolicy, SystemAccessPolicyRule, Reservation,
        SystemActivity, CommandActivity, system_table, command_queue_table,
        cpu_table)
from .scheduler import (Watchdog, TaskBase, Job, RecipeSet, Recipe,
        RecipeTaskResult, MachineRecipe, GuestRecipe, RecipeTask, Log,
        LogRecipe, LogRecipeTask, LogRecipeTaskResult, JobCc, RecipeResource,
        SystemResource, GuestResource, VirtResource, Response, RetentionTag,
        Product, RenderedKickstart, RecipeSetActivity, RecipeRepo,
        RecipeKSAppend, RecipeTaskParam, RecipeSetResponse,
        job_cc_table, recipe_table, recipe_set_table, recipe_resource_table,
        system_resource_table, machine_guest_map, guest_recipe_table,
        recipe_task_table)

class ExternalReport(DeclarativeMappedObject):

    __tablename__ = 'external_reports'
    __table_args__ = {'mysql_engine':'InnoDB'}

    id = Column(Integer, primary_key=True)
    name = Column(Unicode(100), unique=True, nullable=False)
    url = Column(Unicode(10000), nullable=False)
    description = Column(Unicode(1000), default=None)

    def __init__(self, *args, **kw):
        super(ExternalReport, self).__init__(*args, **kw)

# Delayed property definitions due to circular dependencies
class_mapper(LabController).add_property('dyn_systems', dynamic_loader(System))
class_mapper(System).add_properties({
    # The relationship to 'recipe' is complicated
    # by the polymorphism of SystemResource :-(
    'recipes': relation(Recipe, viewonly=True,
        secondary=recipe_resource_table.join(system_resource_table),
        secondaryjoin=and_(system_resource_table.c.id == recipe_resource_table.c.id,
            recipe_resource_table.c.recipe_id == recipe_table.c.id)),
    'dyn_recipes': dynamic_loader(Recipe,
        secondary=recipe_resource_table.join(system_resource_table),
        secondaryjoin=and_(system_resource_table.c.id == recipe_resource_table.c.id,
            recipe_resource_table.c.recipe_id == recipe_table.c.id)),
})
class_mapper(Reservation).add_properties({
    # The relationship to 'recipe' is complicated
    # by the polymorphism of SystemResource :-(
    'recipe': relation(Recipe, uselist=False, viewonly=True,
        secondary=recipe_resource_table.join(system_resource_table),
        secondaryjoin=and_(system_resource_table.c.id == recipe_resource_table.c.id,
            recipe_resource_table.c.recipe_id == recipe_table.c.id)),
})

## Static list of device_classes -- used by master.kid
_device_classes = None
def device_classes():
    global _device_classes
    if not _device_classes:
        _device_classes = DeviceClass.query.all()
    for device_class in _device_classes:
        yield device_class

def auto_cmd_handler(command, new_status):
    if not command.system.open_reservation:
        return
    recipe = command.system.open_reservation.recipe
    if new_status in (CommandStatus.failed, CommandStatus.aborted):
        recipe.abort("Command %s failed" % command.id)
    elif command.action == u'reboot':
        recipe.resource.rebooted = datetime.utcnow()
        first_task = recipe.first_task
        first_task.start()
