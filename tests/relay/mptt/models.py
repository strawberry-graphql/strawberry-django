import django
from django.db import models
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from mptt.models import MPTTModelBase as _MPTTModelBase

if django.VERSION >= (5, 1):
    from django.utils.translation import gettext as _
    from mptt.managers import TreeManager
    from mptt.models import MPTTOptions
    from mptt.utils import _get_tree_model  # noqa: PLC2701

    class MPTTModelBase(_MPTTModelBase):
        @classmethod
        def register(meta, cls, **kwargs):  # noqa: N804
            # For the weird cases when you need to add tree-ness to an *existing*
            # class. For other cases you should subclass MPTTModel instead of calling this.
            if not issubclass(cls, models.Model):
                raise TypeError(_("register() expects a Django model class argument"))

            if not hasattr(cls, "_mptt_meta"):
                cls._mptt_meta = MPTTOptions(**kwargs)

            abstract = getattr(cls._meta, "abstract", False)

            try:
                MPTTModel  # noqa: B018
            except NameError:
                # We're defining the base class right now, so don't do anything
                # We only want to add this stuff to the subclasses.
                # (Otherwise if field names are customized, we'll end up adding two
                # copies)
                pass
            else:
                if not issubclass(cls, MPTTModel):
                    bases = list(cls.__bases__)

                    # strip out bases that are strict superclasses of MPTTModel.
                    # i.e. Model, object
                    # this helps linearize the type hierarchy if possible
                    for i in range(len(bases) - 1, -1, -1):
                        if issubclass(MPTTModel, bases[i]):
                            del bases[i]

                    bases.insert(0, MPTTModel)
                    cls.__bases__ = tuple(bases)

                is_cls_tree_model = _get_tree_model(cls) is cls

                if is_cls_tree_model:
                    # HACK: _meta.get_field() doesn't work before AppCache.ready in Django>=1.8
                    # ( see https://code.djangoproject.com/ticket/24231 )
                    # So the only way to get existing fields is using local_fields on all superclasses.
                    existing_field_names = set()
                    for base in cls.mro():
                        if hasattr(base, "_meta"):
                            existing_field_names.update([
                                f.name for f in base._meta.local_fields
                            ])

                    mptt_meta = cls._mptt_meta
                    indexed_attrs = (mptt_meta.tree_id_attr,)
                    field_names = (
                        mptt_meta.left_attr,
                        mptt_meta.right_attr,
                        mptt_meta.tree_id_attr,
                        mptt_meta.level_attr,
                    )

                    for field_name in field_names:
                        if field_name not in existing_field_names:
                            field = models.PositiveIntegerField(
                                db_index=field_name in indexed_attrs, editable=False
                            )
                            field.contribute_to_class(cls, field_name)

                    # Add an unique_together on tree_id_attr and left_attr, as these are very
                    # commonly queried (pretty much all reads).
                    unique_together = (
                        cls._mptt_meta.tree_id_attr,
                        cls._mptt_meta.left_attr,
                    )
                    if unique_together not in cls._meta.unique_together:
                        cls._meta.unique_together += (unique_together,)

                # Add a tree manager, if there isn't one already
                if not abstract:
                    # make sure we have a tree manager somewhere
                    tree_manager = None
                    # Use the default manager defined on the class if any
                    if cls._default_manager and isinstance(
                        cls._default_manager, TreeManager
                    ):
                        tree_manager = cls._default_manager
                    else:
                        for cls_manager in cls._meta.managers:
                            if (
                                isinstance(cls_manager, TreeManager)
                                and cls_manager.model is cls
                            ):
                                # prefer any locally defined manager (i.e. keep going if not local)
                                tree_manager = cls_manager
                                break

                    if is_cls_tree_model:
                        idx_together = (
                            cls._mptt_meta.tree_id_attr,
                            cls._mptt_meta.left_attr,
                        )

                        if idx_together not in cls._meta.unique_together:
                            cls._meta.unique_together += (idx_together,)

                    if tree_manager and tree_manager.model is not cls:
                        tree_manager = tree_manager._copy_to_model(cls)
                    elif tree_manager is None:
                        tree_manager = TreeManager()
                    tree_manager.contribute_to_class(cls, "_tree_manager")

                    # avoid using ManagerDescriptor, so instances can refer to self._tree_manager
                    cls._tree_manager = tree_manager
            return cls


else:
    MPTTModelBase = _MPTTModelBase


class MPTTAuthor(MPTTModel, metaclass=MPTTModelBase):
    name = models.CharField(max_length=100)
    parent = TreeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
    )


class MPTTBook(models.Model):
    title = models.CharField(max_length=100)
    author = models.ForeignKey(
        MPTTAuthor,
        on_delete=models.CASCADE,
        related_name="books",
    )
