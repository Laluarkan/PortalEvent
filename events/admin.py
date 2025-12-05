from django.contrib import admin
from .models import User, Event, Participant

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_organizer', 'is_staff')

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'organizer', 'date_time', 'price')
    # Exclude slug karena auto-generate
    exclude = ('slug',) 

@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'event', 'is_verified', 'registered_at')
    list_filter = ('event', 'is_verified')