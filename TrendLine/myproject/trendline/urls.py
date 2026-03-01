from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    # Home page
    path('', views.home_view, name='home'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    
    # Dashboard (protected)
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path("get-news/<str:category>/", views.get_news, name="get_news"),
    path('api/trending/', views.get_trending_news, name='get_trending'),
    path('api/trending/advanced/', views.get_advanced_trending_news, name='get_advanced_trending_news'),
    path('api/recent/', views.get_recent_news, name='get_recent'),
    path('api/sidebar/', views.get_sidebar_data, name='get_sidebar_data'),
    path('profile/', views.profile_view, name='profile'),
    path('api/profile/', views.get_profile_api, name='get_profile_api'),
    path('api/profile/update/', views.update_profile_api, name='update_profile_api'),
    path('api/profile/avatar/', views.upload_avatar_api, name='upload_avatar_api'),
    # path('chat-with-bot/', views.chat_with_bot, name='chat_with_bot'),
    path('get-news/', views.get_news_by_topic, name='get_news_by_topic'),
    path('api/chat/', views.NewsChatView.as_view(), name='news_chat'),
    path('api/test/', views.test_api_view, name='test_api'),
    
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)