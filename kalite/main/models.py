import uuid
from django.db import models
from django.db.models import Sum, Avg

from securesync.models import SyncedModel, FacilityUser
import settings

class VideoLog(SyncedModel):
    user = models.ForeignKey(FacilityUser, blank=True, null=True, db_index=True)
    youtube_id = models.CharField(max_length=11, db_index=True)
    total_seconds_watched = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    complete = models.BooleanField(default=False)

    def get_uuid(self, *args, **kwargs):
        namespace = uuid.UUID(self.user.id)
        return uuid.uuid5(namespace, str(self.youtube_id)).hex

    @staticmethod
    def get_points_for_user(user):
        return VideoLog.objects.filter(user=user).aggregate(Sum("points")).get("points__sum", 0) or 0

class ExerciseLog(SyncedModel):
    user = models.ForeignKey(FacilityUser, blank=True, null=True, db_index=True)
    exercise_id = models.CharField(max_length=50, db_index=True)
    streak_progress = models.IntegerField(default=0)
    attempts = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    complete = models.BooleanField(default=False)
    struggling = models.BooleanField(default=False)
    attempts_before_completion = models.IntegerField(blank=True, null=True)
    
    def save(self, *args, **kwargs):
        if self.attempts > 20 and not self.complete:
            self.struggling = True
        already_complete = self.complete
        self.complete = (self.streak_progress >= 100)
        if not already_complete and self.complete:
            self.attempts_before_completion = self.attempts
        super(ExerciseLog, self).save(*args, **kwargs)

    def get_uuid(self, *args, **kwargs):
        namespace = uuid.UUID(self.user.id)
        return uuid.uuid5(namespace, str(self.exercise_id)).hex

    @staticmethod
    def get_points_for_user(user):
        return ExerciseLog.objects.filter(user=user).aggregate(Sum("points")).get("points__sum", 0) or 0

settings.add_syncing_models([VideoLog, ExerciseLog])

class VideoFile(models.Model):
    youtube_id = models.CharField(max_length=11, primary_key=True)
    flagged_for_download = models.BooleanField(default=False)
    download_in_progress = models.BooleanField(default=False)
    priority = models.IntegerField(default=0)
    percent_complete = models.IntegerField(default=0)
    
    class Meta:
        ordering = ["priority", "youtube_id"]

class Settings(models.Model):
    name = models.CharField(max_length=30, primary_key=True)
    value = models.TextField(blank=True)
    datatype = models.CharField(max_length=10, default="str")
    
    @staticmethod
    def set(name, value):
        setting = Settings(name=name, value=str(value), datatype=value.__class__.__name__)
        setting.save()
        
    @staticmethod
    def get(name):
        try:
            setting = Settings.objects.get(name=name)
            if setting.datatype == "int":
                return int(setting.value)
            if setting.datatype == "float":
                return float(setting.value)
            return setting.value
        except Settings.DoesNotExist:
            return ""
        