from django.contrib import admin
from .models import UserProfile, Timetable, Product, Notification

admin.site.register(UserProfile)
admin.site.register(Timetable)
admin.site.register(Product)
admin.site.register(Notification)
