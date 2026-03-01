from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone
from datetime import timedelta
from .models import UserProfile, LoginSession, UserActivity, ChatConversation, ChatMessage


# Inline admin for UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('phone_number', 'alternate_email')
        }),
        ('Personal Information', {
            'fields': ('bio', 'location', 'birth_date', 'gender')
        }),
        ('Media', {
            'fields': ('avatar', 'cover_image')
        }),
        ('Social Media', {
            'fields': ('website', 'linkedin', 'twitter', 'github'),
            'classes': ('collapse',)
        }),
        ('Preferences', {
            'fields': ('timezone', 'language')
        }),
        ('Privacy Settings', {
            'fields': ('show_email', 'show_phone', 'show_birth_date'),
            'classes': ('collapse',)
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'sms_notifications', 'marketing_emails'),
            'classes': ('collapse',)
        }),
    )


# Unregister the original User admin
admin.site.unregister(User)


# Custom User Admin with filtering
@admin.register(User)
class CustomUserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined')
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        ('date_joined', admin.DateFieldListFilter),
    )
    
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    
    # Custom filters
    def get_list_filter(self, request):
        filters = list(super().get_list_filter(request))
        filters.extend([
            RecentlyJoinedFilter,
        ])
        return filters


class RecentlyJoinedFilter(admin.SimpleListFilter):
    title = 'Recently Joined'
    parameter_name = 'recently_joined'
    
    def lookups(self, request, model_admin):
        return (
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('week', 'This Week'),
            ('month', 'This Month'),
        )
    
    def queryset(self, request, queryset):
        now = timezone.now()
        
        if self.value() == 'today':
            return queryset.filter(date_joined__date=now.date())
        
        if self.value() == 'yesterday':
            yesterday = now.date() - timedelta(days=1)
            return queryset.filter(date_joined__date=yesterday)
        
        if self.value() == 'week':
            week_ago = now - timedelta(days=7)
            return queryset.filter(date_joined__gte=week_ago)
        
        if self.value() == 'month':
            month_ago = now - timedelta(days=30)
            return queryset.filter(date_joined__gte=month_ago)


# class Last10DaysFilter(admin.SimpleListFilter):
#     title = 'Last 10 Days'
#     parameter_name = 'last_10_days'
    
#     def lookups(self, request, model_admin):
#         return (
#             ('yes', 'Last 10 Days'),
#         )
    
#     def queryset(self, request, queryset):
#         if self.value() == 'yes':
#             ten_days_ago = timezone.now() - timedelta(days=10)
#             return queryset.filter(date_joined__gte=ten_days_ago)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone_number', 'location', 'created_at', 'updated_at')
    list_filter = ('gender', 'timezone', 'created_at', 'email_notifications')
    search_fields = ('user__username', 'user__email', 'phone_number', 'location')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'alternate_email')
        }),
        ('Personal Information', {
            'fields': ('bio', 'location', 'birth_date', 'gender')
        }),
        ('Media', {
            'fields': ('avatar', 'cover_image')
        }),
        ('Social Media', {
            'fields': ('website', 'linkedin', 'twitter', 'github')
        }),
        ('Preferences', {
            'fields': ('timezone', 'language')
        }),
        ('Privacy Settings', {
            'fields': ('show_email', 'show_phone', 'show_birth_date')
        }),
        ('Notifications', {
            'fields': ('email_notifications', 'sms_notifications', 'marketing_emails')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LoginSession)
class LoginSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'login_time', 'logout_time', 'ip_address', 'is_active', 'country', 'city')
    list_filter = ('is_active', 'login_time', 'country')
    search_fields = ('user__username', 'user__email', 'ip_address', 'country', 'city')
    readonly_fields = ('login_time', 'duration')
    date_hierarchy = 'login_time'
    
    fieldsets = (
        ('User Information', {
            'fields': ('user', 'session_key', 'is_active')
        }),
        ('Session Details', {
            'fields': ('login_time', 'logout_time', 'duration')
        }),
        ('Technical Information', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Location', {
            'fields': ('country', 'city')
        }),
    )
    
    def duration(self, obj):
        return obj.duration()
    duration.short_description = 'Session Duration'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'timestamp', 'ip_address')
    list_filter = ('activity_type', 'timestamp')
    search_fields = ('user__username', 'user__email', 'description', 'ip_address')
    readonly_fields = ('timestamp',)
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('User & Activity', {
            'fields': ('user', 'activity_type', 'description')
        }),
        ('Technical Details', {
            'fields': ('timestamp', 'ip_address', 'user_agent')
        }),
        ('Additional Data', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
    )


# Customize admin site header and title
admin.site.site_header = "User Management Admin"
admin.site.site_title = "User Admin Portal"
admin.site.index_title = "Welcome to User Management Portal"