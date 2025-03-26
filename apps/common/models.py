from django.db import models
from django.db.models import Manager
from django.utils.timezone import now


class SoftDeleteQuerySet(models.QuerySet):
    """Custom queryset for Soft delete."""

    def _soft_delete(self):
        """Write a soft delete method."""
        return self.update(is_deleted=True, deleted_at=now())

    def delete(self):
        """Rewrite the default delete method."""
        return self._soft_delete()

    def hard_delete(self):
        """Hard delete method to use the default delete method."""
        return super().delete()

    def restore(self):
        """Restore method to restore data."""
        return self.update(is_deleted=False, deleted_at=None)

    def deleted(self):
        """Method for filter the deleted data."""
        return self.filter(is_deleted=True)

    def active(self):
        """Method for filter the data which is not deleted."""
        return self.filter(is_deleted=False)


class SoftDeleteManager(Manager):
    """Custom manager for soft delete."""
    def get_queryset(self):
        """Rewrite the default get queryset method."""
        return SoftDeleteQuerySet(self.model, using=self._db).active()

    def get_all(self):
        """Method to get all data."""
        return SoftDeleteQuerySet(self.model, using=self._db)

    def deleted_only(self):
        """Method to get just deleted data."""
        return SoftDeleteQuerySet(self.model, using=self._db).deleted()


class SoftDeleteModel(models.Model):
    """An Abstract model for soft delete"""
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)

    objects_default = Manager()
    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def _soft_delete(self):
        """Soft delete method to delete the record and related records too."""
        if self.is_deleted is True:
            return
        self.is_deleted = True
        self.deleted_at = now()
        self.save()
        for related in self._meta.related_objects:
            if related.on_delete == models.CASCADE:
                related_name = related.get_accessor_name()
                related_manager = getattr(self, related_name, None)
                if related_manager and hasattr(related_manager, "all"):
                    related_queryset = related_manager.all()
                    related_model = related_queryset.model
                    if issubclass(related_model, SoftDeleteModel):
                        related_manager.all().update(is_deleted=True, deleted_at=now())

    def delete(self):
        """Rewrite the default delete method."""
        return self._soft_delete()

    def restore(self):
        """"Restore method to restore the record and related records too."""
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_at = None
        self.save()

        for related in self._meta.related_objects:
            if related.on_delete == models.CASCADE:
                related_name = related.get_accessor_name()
                related_manager = getattr(self, related_name, None)
                if related_manager and hasattr(related_manager, "deleted_only"):
                    related_queryset = related_manager.deleted_only()
                    related_model = related_queryset.model
                    if issubclass(related_model, SoftDeleteModel):
                        related_manager.all().update(is_deleted=False, deleted_at=None)

    def hard_delete(self):
        """Hard delete method as default delete"""
        return super().delete()
