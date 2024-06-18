from django.db import models


# Create your models here.
class User(models.Model):
    phone_number = models.CharField(max_length=100)
    topic = models.CharField(blank=True, max_length=50, null=True)
    username = models.CharField(blank=True, max_length=50, null=True)
    current_question_index = models.IntegerField(blank=True, null=True)
    score = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    survey_response = models.CharField(blank=True, max_length=50, null=True)

    def __str__(self):
        return f"{self.phone_number} - {self.topic} - Score: {self.score}"
