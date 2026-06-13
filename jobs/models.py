from django.db import models

# Create your models here.
class Candidate(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    role = models.CharField(max_length=100)
    employment_type = models.CharField(
        max_length=20,
        default="C2C"
    )
    # C2C, W2, etc.
    resume = models.FileField(upload_to="resumes/")
    score = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        default="PENDING"
    )