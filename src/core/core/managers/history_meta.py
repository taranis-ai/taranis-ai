"""Versioned mixin class and other utilities."""

from datetime import timezone, datetime

from core.log import logger
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import event
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import func
from sqlalchemy import inspect
from sqlalchemy import Integer
from sqlalchemy import PrimaryKeyConstraint
from sqlalchemy import select
from sqlalchemy import and_
from sqlalchemy import util
from sqlalchemy.orm import attributes
from sqlalchemy.orm import object_mapper
from sqlalchemy.orm.exc import UnmappedColumnError
from sqlalchemy.orm.relationships import RelationshipProperty


def col_references_table(col, table):
    for fk in col.foreign_keys:
        if fk.references(table):
            return True
    return False


def _is_versioning_col(col):
    return "version_meta" in col.info


def _history_mapper(local_mapper):
    cls = local_mapper.class_

    if cls.__dict__.get("_history_mapper_configured", False):
        return

    cls._history_mapper_configured = True

    super_mapper = local_mapper.inherits
    polymorphic_on = None
    super_fks = []
    properties = util.OrderedDict()

    if super_mapper:
        super_history_mapper = super_mapper.class_.__history_mapper__
    else:
        super_history_mapper = None

    if not super_mapper or local_mapper.local_table is not super_mapper.local_table:
        version_meta = {"version_meta": True}  # add column.info to identify
        # columns specific to versioning

        history_table = local_mapper.local_table.to_metadata(
            local_mapper.local_table.metadata,
            name=local_mapper.local_table.name + "_history",
        )
        for idx in history_table.indexes:
            if idx.name is not None:
                idx.name += "_history"
            idx.unique = False

        for orig_c, history_c in zip(local_mapper.local_table.c, history_table.c):
            orig_c.info["history_copy"] = history_c
            history_c.unique = False
            history_c.default = history_c.server_default = None
            history_c.autoincrement = False

            if super_mapper and col_references_table(orig_c, super_mapper.local_table):
                assert super_history_mapper is not None
                super_fks.append(
                    (
                        history_c.key,
                        list(super_history_mapper.local_table.primary_key)[0],
                    )
                )
            if orig_c is local_mapper.polymorphic_on:
                polymorphic_on = history_c

            orig_prop = local_mapper.get_property_by_column(orig_c)
            # carry over column re-mappings
            if len(orig_prop.columns) > 1 or orig_prop.columns[0].key != orig_prop.key:
                properties[orig_prop.key] = tuple(col.info["history_copy"] for col in orig_prop.columns)

        for const in list(history_table.constraints):
            if not isinstance(const, (PrimaryKeyConstraint, ForeignKeyConstraint)):
                history_table.constraints.discard(const)

        # "version" stores the integer version id.  This column is
        # required.
        history_table.append_column(
            Column(
                "version",
                Integer,
                primary_key=True,
                autoincrement=False,
                info=version_meta,
            )
        )

        # "changed" column stores the UTC timestamp of when the
        # history row was created.
        # This column is optional and can be omitted.
        history_table.append_column(
            Column(
                "changed",
                DateTime,
                default=lambda: datetime.now(timezone.utc),
                info=version_meta,
            )
        )

        # Check if this is a VersionedRelation class and add parent version columns
        is_versioned_relation = issubclass(cls, VersionedRelation) if hasattr(cls.__bases__[0] if cls.__bases__ else object, '__name__') else False
        if is_versioned_relation:
            # Add parent version tracking columns for relationship tables
            # These will be populated when creating history entries
            for fk_constraint in history_table.foreign_key_constraints:
                for fk in fk_constraint.elements:
                    # Extract table name from foreign key string (e.g., "story.id" -> "story")
                    if isinstance(fk._colspec, str):
                        referenced_table = fk._colspec.split('.')[0]
                        parent_version_col_name = f"{referenced_table}_version"
                        
                        # Add the parent version column if it doesn't already exist
                        if not any(col.name == parent_version_col_name for col in history_table.columns):
                            history_table.append_column(
                                Column(
                                    parent_version_col_name,
                                    Integer,
                                    default=1,
                                    info=version_meta,
                                )
                            )

        if super_mapper:
            # No version column foreign key since we're not adding version to main table
            pass

        if super_fks:
            history_table.append_constraint(ForeignKeyConstraint(*zip(*super_fks)))

    else:
        history_table = None
        super_history_table = super_mapper.local_table.metadata.tables[super_mapper.local_table.name + "_history"]

        # single table inheritance.  take any additional columns that may have
        # been added and add them to the history table.
        for column in local_mapper.local_table.c:
            if column.key not in super_history_table.c:
                col = Column(column.name, column.type, nullable=column.nullable)
                super_history_table.append_column(col)

    # Note: We do NOT add a version column to the main table!
    # Instead, we track versions only in the history table.
    # The current object will use a version from memory/session context.

    # set the "active_history" flag
    # on on column-mapped attributes so that the old version
    # of the info is always loaded (currently sets it on all attributes)
    for prop in local_mapper.iterate_properties:
        prop.active_history = True

    super_mapper = local_mapper.inherits

    if super_history_mapper:
        bases = (super_history_mapper.class_,)

        if history_table is not None:
            properties["changed"] = (history_table.c.changed,) + tuple(super_history_mapper.attrs.changed.columns)

    else:
        bases = local_mapper.base_mapper.class_.__bases__

    versioned_cls = type(
        "%sHistory" % cls.__name__,
        bases,
        {
            "_history_mapper_configured": True,
            "__table__": history_table,
            "__mapper_args__": dict(
                inherits=super_history_mapper,
                polymorphic_identity=local_mapper.polymorphic_identity,
                polymorphic_on=polymorphic_on,
                properties=properties,
            ),
        },
    )

    cls.__history_mapper__ = versioned_cls.__mapper__


class Versioned:
    use_mapper_versioning = False
    """if True, also assign the version column to be tracked by the mapper"""

    __table_args__ = {"sqlite_autoincrement": True}
    """Use sqlite_autoincrement, to ensure unique integer values
    are used for new rows even for rows that have been deleted."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Track version in memory instead of database column
        self._version = 1

    @property
    def version(self):
        return getattr(self, "_version", 1)

    @version.setter
    def version(self, value):
        self._version = value

    def __init_subclass__(cls) -> None:
        insp = inspect(cls, raiseerr=False)

        if insp is not None:
            _history_mapper(insp)
        else:

            @event.listens_for(cls, "after_mapper_constructed")
            def _mapper_constructed(mapper, class_):
                _history_mapper(mapper)

        super().__init_subclass__()


class VersionedRelation(Versioned):
    """
    Specialized versioning for many-to-many relationship tables.
    
    This class extends Versioned to add parent version tracking for junction tables.
    When a relationship history entry is created, it will also store the versions
    of the related parent entities at the time the relationship was established.
    
    Example:
        class StoryNewsItemAttribute(VersionedRelation, BaseModel):
            story_id = db.Column(db.String(64), db.ForeignKey("story.id"), primary_key=True)
            news_item_attribute_id = db.Column(db.String(64), db.ForeignKey("news_item_attribute.id"), primary_key=True)
            # ... other columns
            
    This will automatically create a history table with additional columns:
    - story_version: Version of the Story when this relationship was created
    - news_item_attribute_version: Version of the NewsItemAttribute when this relationship was created
    """
    
    def get_parent_versions(self):
        """
        Get the current versions of all parent entities.
        This method should be called when creating history entries to capture
        the current state of related entities.
        
        Returns:
            dict: Mapping of parent table names to their current versions
        """
        parent_versions = {}
        
        # Get the mapper for this class
        mapper = object_mapper(self)
        
        # Iterate through foreign key relationships to find parent entities
        for fk in mapper.local_table.foreign_key_columns:
            if fk.name.endswith('_id'):
                parent_table_name = fk.name[:-3]  # Remove '_id' suffix
                parent_id = getattr(self, fk.name)
                
                if parent_id:
                    # Try to get the parent object and its version
                    # This is a simplified approach - in practice you might need
                    # more sophisticated logic to resolve the parent class
                    try:
                        parent_obj = getattr(self, parent_table_name, None)
                        if parent_obj and hasattr(parent_obj, 'version'):
                            parent_versions[f"{parent_table_name}_version"] = parent_obj.version
                    except AttributeError:
                        # If we can't resolve the parent, set version to 1 as default
                        parent_versions[f"{parent_table_name}_version"] = 1
        
        return parent_versions

        super().__init_subclass__()


def versioned_objects(iter_):
    for obj in iter_:
        if hasattr(obj, "__history_mapper__"):
            yield obj


def create_version(obj, session, deleted=False, created=False):
    obj_mapper = object_mapper(obj)
    history_mapper = obj.__history_mapper__
    history_cls = history_mapper.class_

    attr = {}

    obj_changed = False
    # import pdb; pdb.set_trace()
    # logger.debug(f"Checking changes for object: {obj}")

    for om, hm in zip(obj_mapper.iterate_to_root(), history_mapper.iterate_to_root()):
        if hm.single:
            continue

        for hist_col in hm.local_table.c:
            if _is_versioning_col(hist_col):
                continue

            obj_col = om.local_table.c[hist_col.key]

            try:
                prop = obj_mapper.get_property_by_column(obj_col)
            except UnmappedColumnError:
                continue

            # Always use the current value of the property for the history entry
            attr[prop.key] = getattr(obj, prop.key)

            # For change detection, keep the old logic
            a, u, d = attributes.get_history(obj, prop.key)
            if d or a:
                obj_changed = True

    if not obj_changed:
        # not changed, but we have relationships.  OK
        # check those too
        for prop in obj_mapper.iterate_properties:
            if (
                isinstance(prop, RelationshipProperty)
                and attributes.get_history(obj, prop.key, passive=attributes.PASSIVE_NO_INITIALIZE).has_changes()
            ):
                for p in prop.local_columns:
                    if p.foreign_keys:
                        obj_changed = True
                        break
                if obj_changed is True:
                    break

    if not obj_changed and not deleted and not created:
        return

    # Calculate the next version based on history table
    history_table = history_mapper.local_table
    pk_columns = inspect(obj_mapper.local_table).primary_key
    conditions = []
    for pk_col in pk_columns:
        pk_value = getattr(obj, pk_col.name)
        conditions.append(history_table.c[pk_col.name] == pk_value)

    if conditions:
        max_version = session.execute(select(func.coalesce(func.max(history_table.c.version), 0)).where(and_(*conditions))).scalar()
        next_version = (max_version or 0) + 1
    else:
        next_version = 1

    attr["version"] = next_version

    hist = history_cls()
    for key, value in attr.items():
        setattr(hist, key, value)
    session.add(hist)

    # Update the in-memory version counter
    obj.version = next_version


def versioned_session(session):
    @event.listens_for(session, "before_flush")
    def before_flush(session, flush_context, instances):
        logger.debug("before_flush versioning")

        if not hasattr(session, "_versioned_objs"):
            session._versioned_objs = set()

        for obj in versioned_objects(session.new):
            # 🚨 Skip join-table entries that don't yet have FK values
            if hasattr(obj, "story_id") and getattr(obj, "story_id", None) is None:
                logger.debug(f"Skipping versioning for {obj} (missing story_id)")
                continue
            if hasattr(obj, "news_item_attribute_id") and getattr(obj, "news_item_attribute_id", None) is None:
                logger.debug(f"Skipping versioning for {obj} (missing news_item_attribute_id)")
                continue

            if obj not in session._versioned_objs:
                create_version(obj, session, created=True)
                session._versioned_objs.add(obj)

        for obj in versioned_objects(session.deleted):
            if obj not in session._versioned_objs:
                create_version(obj, session, deleted=True)
                session._versioned_objs.add(obj)

    @event.listens_for(session, "after_flush")
    def after_flush(session, flush_context):
        logger.debug("after_flush versioning")

        if not hasattr(session, "_versioned_objs"):
            session._versioned_objs = set()

        for obj in versioned_objects(session.dirty):
            state = attributes.instance_state(obj)
            if state.persistent and obj not in session._versioned_objs:
                create_version(obj, session)
                session._versioned_objs.add(obj)

        # Reset between flushes
        session._versioned_objs.clear()


# def register_relationship_history_hooks(Base, versioned_cls):
#     """
#     Attach append/remove listeners for all many-to-many (secondary) relationships
#     of Versioned subclasses. Marks parent as dirty so the versioning system
#     can record relationship changes during flush.
#     """

#     _REGISTERED_REL_HOOKS = set()

#     for mapper in Base.registry.mappers:
#         cls = mapper.class_

#         if not issubclass(cls, versioned_cls):
#             continue

#         for prop in mapper.relationships:
#             if not isinstance(prop, RelationshipProperty):
#                 continue
#             if prop.secondary is None:
#                 continue  # only many-to-many relationships

#             rel_name = prop.key
#             target_cls = prop.entity.class_
#             key = (cls, rel_name)
#             if key in _REGISTERED_REL_HOOKS:
#                 continue
#             _REGISTERED_REL_HOOKS.add(key)

#             # --- helper to safely flag modifications --------------------------------
#             def _safe_flag_modified(instance, attr_name):
#                 """Mark instance attribute as modified, even if unloaded."""
#                 state = inspect(instance)
#                 if attr_name in state.attrs:
#                     try:
#                         flag_modified(instance, attr_name)
#                     except Exception as exc:
#                         logger.debug(f"Could not flag_modified({attr_name}): {exc}")
#                 else:
#                     logger.debug(f"Skipped flag_modified({attr_name}) – attribute not loaded")
#                 try:
#                     flag_dirty(instance)
#                 except Exception as exc:
#                     logger.debug(f"Could not flag_dirty({attr_name}): {exc}")

#             # --- on append -----------------------------------------------------------
#             @event.listens_for(getattr(cls, rel_name), "append", propagate=True)
#             def on_append(instance, related_obj, initiator,
#                           cls=cls, rel_name=rel_name):
#                 sess = inspect(instance).session
#                 now = datetime.now(timezone.utc)
#                 logger.debug(
#                     f"[REL-ADD] {cls.__name__}.{rel_name}: "
#                     f"{instance} → {related_obj} @ {now.isoformat()}"
#                 )
#                 if sess is not None:
#                     with sess.no_autoflush:
#                         _safe_flag_modified(instance, rel_name)

#             # --- on remove -----------------------------------------------------------
#             @event.listens_for(getattr(cls, rel_name), "remove", propagate=True)
#             def on_remove(instance, related_obj, initiator,
#                           cls=cls, rel_name=rel_name, target_cls=target_cls):
#                 sess = inspect(instance).session
#                 now = datetime.now(timezone.utc)
#                 logger.debug(
#                     f"[REL-REMOVE] {cls.__name__}.{rel_name}: "
#                     f"{instance} ⟷ {target_cls.__name__}({related_obj}) "
#                     f"removed @ {now.isoformat()}"
#                 )
#                 if sess is not None:
#                     with sess.no_autoflush:
#                         _safe_flag_modified(instance, rel_name)
