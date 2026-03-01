from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import CustomUserCreationForm, CustomAuthenticationForm
from django.utils import timezone
import logging
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, timedelta
from django.views.decorators.http import require_http_methods
from .models import UserProfile, LoginSession, UserActivity
import re
from django.views import View
from django.utils.decorators import method_decorator

# NewsAPI configuration
NEWS_API_KEY = "81509bdd2f3d4205bff00a258afce41b"
NEWS_BASE_URL = "https://newsapi.org/v2/everything"

def extract_news_topic(message):
    """Extract news topic from user message"""
    message = message.lower().strip()
    
    # Common news topics mapping
    topic_keywords = {
        'cricket': ['cricket', 'ipl', 'bcci', 'match', 'wicket', 'batting', 'bowling'],
        'politics': ['politics', 'election', 'government', 'minister', 'parliament', 'bjp', 'congress'],
        'technology': ['technology', 'tech', 'ai', 'artificial intelligence', 'software', 'computer', 'mobile'],
        'sports': ['sports', 'football', 'basketball', 'tennis', 'olympics', 'fifa'],
        'business': ['business', 'economy', 'stock', 'market', 'finance', 'company'],
        'health': ['health', 'medicine', 'covid', 'vaccine', 'hospital', 'doctor'],
        'entertainment': ['movie', 'bollywood', 'hollywood', 'actor', 'actress', 'cinema', 'film'],
        'weather': ['weather', 'rain', 'temperature', 'climate', 'storm', 'cyclone'],
    }
    
    # Check for specific topic mentions
    for topic, keywords in topic_keywords.items():
        for keyword in keywords:
            if keyword in message:
                return topic
    
    # Check for generic news requests
    news_patterns = [
        r'news about (.+)',
        r'latest (.+) news',
        r'(.+) news',
        r'tell me about (.+)',
        r'what.*happening.*(.+)',
    ]
    
    for pattern in news_patterns:
        match = re.search(pattern, message)
        if match:
            topic = match.group(1).strip()
            # Clean up common words
            topic = re.sub(r'\b(the|in|of|and|or|but|news)\b', '', topic).strip()
            if topic:
                return topic
    
    return 'India'  # Default topic

def fetch_news_from_api(query, days_back=10):
    """Fetch news from NewsAPI"""
    try:
        # Calculate date range
        today = datetime.now().strftime('%Y-%m-%d')
        past_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        # Construct API URL
        params = {
            'q': query,
            'from': past_date,
            'to': today,
            'sortBy': 'publishedAt',
            'language': 'en',
            'pageSize': 10,
            'apiKey': NEWS_API_KEY
        }
        
        response = requests.get(NEWS_BASE_URL, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok' and data.get('articles'):
                return data['articles']
            else:
                return None
        else:
            print(f"API Error: {response.status_code}")
            return None
            
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None
    except Exception as e:
        print(f"Error fetching news: {e}")
        return None

def format_news_response(articles, topic):
    """Format news articles into a readable response"""
    if not articles:
        return f"Sorry, I couldn't find any recent news about {topic}. Please try a different topic."
    
    response = f"📰 **Latest {topic.title()} News:**\n\n"
    
    for i, article in enumerate(articles[:5], 1):  # Limit to 5 articles
        title = article.get('title', 'No title')
        description = article.get('description', 'No description available')
        url = article.get('url', '#')
        published_at = article.get('publishedAt', '')
        source = article.get('source', {}).get('name', 'Unknown')
        
        # Format date
        try:
            if published_at:
                date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime('%B %d, %Y')
            else:
                formatted_date = 'Unknown date'
        except:
            formatted_date = 'Unknown date'
        
        # Truncate description if too long
        if description and len(description) > 150:
            description = description[:150] + "..."
        
        response += f"**{i}. {title}**\n"
        response += f"📅 {formatted_date} | 📰 {source}\n"
        if description:
            response += f"📝 {description}\n"
        response += f"🔗 [Read more]({url})\n\n"
    
    return response

def process_news_query(user_message):
    """Main function to process user's news query"""
    # Handle greetings and general queries
    greetings = ['hello', 'hi', 'hey', 'help', 'start']
    if any(greeting in user_message.lower() for greeting in greetings):
        return ("👋 Hello! I'm your News Assistant. I can help you find the latest news on various topics. "
                "Just ask me about:\n"
                "• Cricket news\n"
                "• Politics updates\n"
                "• Technology news\n"
                "• Sports updates\n"
                "• Business news\n"
                "• Or any other topic!\n\n"
                "Example: 'Show me cricket news' or 'Latest technology updates'")
    
    # Extract topic from user message
    topic = extract_news_topic(user_message)
    
    # Fetch news articles
    articles = fetch_news_from_api(topic)
    
    # Format and return response
    return format_news_response(articles, topic)

@csrf_exempt
@require_http_methods(["POST"])
def chat_with_bot(request):
    """Handle chatbot queries about news"""
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return JsonResponse({
                "status": "error",
                "message": "Please provide a message"
            })
        
        # Process the news query
        bot_response = process_news_query(user_message)
        
        return JsonResponse({
            "status": "success",
            "bot_response": bot_response,
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON format"
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        })

# Alternative function for direct topic queries
@csrf_exempt
@require_http_methods(["GET"])
def get_news_by_topic(request):
    """Get news for a specific topic via GET request"""
    topic = request.GET.get('topic', 'India')
    days = int(request.GET.get('days', 10))
    
    try:
        articles = fetch_news_from_api(topic, days)
        response = format_news_response(articles, topic)
        
        return JsonResponse({
            "status": "success",
            "topic": topic,
            "news": response,
            "article_count": len(articles) if articles else 0,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({
            "status": "error",
            "message": f"Error fetching news: {str(e)}"
        })


# Set up logging
logger = logging.getLogger(__name__)
#User = get_user_model()


def home_view(request):
    """
    Home page view - accessible to all users (not login required)
    Shows preview of news features with limited categories
    Chatbot feature requires authentication
    """
    # If user is already authenticated, redirect to dashboard
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    # Log page access for analytics (optional)
    logger.info('Home page accessed by anonymous user')
    
    context = {
        'title': 'TrendLine - Your News Hub',
        'page_type': 'home',
        'show_auth_buttons': True,  # Show login/register buttons
        'chatbot_locked': True,  # Chatbot is locked for non-authenticated users
        'categories': [
            'politics',
            'sports', 
            'technology',
            'bollywood',
            'business'
        ],  # Limited categories (half of dashboard)
    }
    
    return render(request, 'trendline/home.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                # Save the user - signal will auto-create UserProfile
                user = form.save()
                
                # Log successful registration
                logger.info(f'New user registered: {user.username} (ID: {user.id})')
                
                username = form.cleaned_data.get('username')
                messages.success(request, f'Account created for {username}! You can now log in.')
                
                # Auto login after registration
                authenticated_user = authenticate(
                    request,
                    username=form.cleaned_data['username'],
                    password=form.cleaned_data['password1']
                )
                
                if authenticated_user:
                    login(request, authenticated_user)
                    
                    # Create login session
                    LoginSession.objects.create(
                        user=authenticated_user,
                        login_time=timezone.now(),
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        session_key=request.session.session_key or 'unknown'
                    )
                    
                    # Log registration activity
                    UserActivity.objects.create(
                        user=authenticated_user,
                        activity_type='REGISTER',
                        description='User registered and auto-logged in',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        metadata={'registration_method': 'form'}
                    )
                    
                    logger.info(f'User {authenticated_user.username} logged in after registration')
                    
                    return redirect('dashboard')
                    
            except Exception as e:
                logger.error(f'Error during user registration: {str(e)}')
                messages.error(request, 'An error occurred during registration. Please try again.')
                
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomUserCreationForm()
    
    context = {
        'form': form,
        'title': 'TrendLine - Register',
        'page_type': 'register'
    }
    return render(request, 'trendline/register.html', context)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = CustomAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            user = authenticate(request, username=username, password=password)

            if user is not None:
                try:
                    # Login the user
                    login(request, user)
                    
                    # Update and save login details
                    user.last_login = timezone.now()
                    user.save(update_fields=['last_login'])
                    
                    # Create login session record
                    LoginSession.objects.create(
                        user=user,
                        login_time=timezone.now(),
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        session_key=request.session.session_key or 'unknown'
                    )
                    
                    # Ensure user has a profile
                    profile, profile_created = UserProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            'bio': '',
                            'location': '',
                            'timezone': 'UTC',
                            'language': 'en',
                            'email_notifications': True,
                        }
                    )
                    
                    # Log login activity
                    UserActivity.objects.create(
                        user=user,
                        activity_type='LOGIN',
                        description='User logged in successfully',
                        ip_address=get_client_ip(request),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        metadata={
                            'login_method': 'form',
                            'session_key': request.session.session_key,
                            'profile_created': profile_created
                        }
                    )
                    
                    # Log successful login
                    logger.info(f'User {user.username} logged in successfully. Profile exists: {not profile_created}')
                    
                    messages.success(request, f'Welcome back, {user.first_name or user.username}!')

                    next_page = request.GET.get('next')
                    return redirect(next_page if next_page else 'dashboard')
                    
                except Exception as e:
                    logger.error(f'Error during login for user {username}: {str(e)}')
                    messages.error(request, 'An error occurred during login. Please try again.')
            else:
                messages.error(request, 'Invalid username or password.')
                # Log failed login attempt
                logger.warning(f'Failed login attempt for username: {username}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = CustomAuthenticationForm()

    context = {
        'form': form,
        'title': 'TrendLine - Login',
        'page_type': 'login'
    }
    return render(request, 'trendline/login.html', context)


@login_required
def dashboard_view(request):
    """User dashboard after login"""
    try:
        # Temporarily comment out until migration is complete
        # request.user.last_activity = timezone.now()
        # request.user.save(update_fields=['last_activity'])
        
        # Log dashboard access
        logger.info(f'User {request.user.username} accessed dashboard')
        
        # Log dashboard activity
        UserActivity.objects.create(
            user=request.user,
            activity_type='DASHBOARD_VIEW',
            description='User accessed dashboard',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        context = {
            'title': 'TrendLine - Dashboard',
            'user': request.user,
            'last_login': request.user.last_login,
            'date_joined': request.user.date_joined,
        }
        return render(request, 'trendline/dashboard.html', context)
        
    except Exception as e:
        logger.error(f'Error in dashboard view for user {request.user.username}: {str(e)}')
        messages.error(request, 'An error occurred loading the dashboard.')
        return redirect('home')


def logout_view(request):
    if request.method in ["POST", "GET"]:
        try:
            username = request.user.username if request.user.is_authenticated else 'Anonymous'
            
            # Update login session
            if request.user.is_authenticated:
                try:
                    session = LoginSession.objects.filter(
                        user=request.user,
                        session_key=request.session.session_key,
                        is_active=True
                    ).first()
                    if session:
                        session.logout_time = timezone.now()
                        session.is_active = False
                        session.save()
                except Exception as e:
                    logger.warning(f'Error updating login session for {username}: {str(e)}')
                
                # Log logout activity
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='LOGOUT',
                    description='User logged out',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    metadata={'logout_method': request.method.lower()}
                )
            
            logout(request)
            
            # Log successful logout
            logger.info(f'User {username} logged out successfully')
            
            messages.info(request, 'You have been successfully logged out.')
            return redirect('home')
            
        except Exception as e:
            logger.error(f'Error during logout: {str(e)}')
            logout(request)  # Still logout even if there's an error
            return redirect('home')
    return redirect('home')



def get_page_context(page_type):
    """Helper function to get page-specific context"""
    contexts = {
        'home': {
            'welcome_message': 'Welcome to TrendLine',
            'subtitle': 'Your Gateway to Success'
        },
        'register': {
            'side_message': 'Join TrendLine Today!',
            'side_subtitle': 'Create your account and start your journey with us.'
        },
        'login': {
            'side_message': 'Welcome Back!',
            'side_subtitle': 'Sign in to continue your TrendLine experience.'
        }
    }
    return contexts.get(page_type, {})


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


# Additional view for updating user profile
@login_required
def update_profile_view(request):
    """Allow users to update their profile information"""
    if request.method == 'POST':
        try:
            user = request.user
            profile, created = UserProfile.objects.get_or_create(user=user)
            
            # Update user fields from form data
            user.first_name = request.POST.get('first_name', user.first_name)
            user.last_name = request.POST.get('last_name', user.last_name)
            user.email = request.POST.get('email', user.email)
            
            # Update profile fields
            profile.phone_number = request.POST.get('phone_number', profile.phone_number)
            profile.bio = request.POST.get('bio', profile.bio)
            profile.location = request.POST.get('location', profile.location)
            
            # Save all changes to database
            user.save()
            profile.save()
            
            # Log profile update activity
            UserActivity.objects.create(
                user=user,
                activity_type='PROFILE_UPDATE',
                description='Profile updated via form',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={'update_method': 'form'}
            )
            
            # Log profile update
            logger.info(f'User {user.username} updated their profile')
            
            messages.success(request, 'Profile updated successfully!')
            return redirect('dashboard')
            
        except Exception as e:
            logger.error(f'Error updating profile for user {request.user.username}: {str(e)}')
            messages.error(request, 'An error occurred while updating your profile.')
    
    context = {
        'title': 'TrendLine - Update Profile',
        'user': request.user
    }
    return render(request, 'trendline/update_profile.html', context)



def get_news(request, category):
    api_key = "81509bdd2f3d4205bff00a258afce41b"

    category_mapping = {
        # "all": "India",
        "politics": "India politics government",
        "bollywood": "India bollywood entertainment movies",
        "sports": "India sports cricket football",
        "technology": "India technology gadgets innovation",
        "business": "India business economy finance",
        "health": "India health medicine covid",
        "international": "world news global international relations",
        "science": "science research space ISRO NASA discovery",
        "environment": "India environment climate change pollution",
        "education": "India education schools universities students",
        "lifestyle": "India lifestyle fashion food travel culture"
    }

    query = category_mapping.get(category, "India")
    search_query = request.GET.get("q", "")

    # Use top-headlines for all, everything for specific categories
    if category == "all":
        url = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={api_key}"
    else:
        url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&apiKey={api_key}"

    response = requests.get(url)
    data = response.json()
    articles = data.get("articles", [])

    if search_query:
        articles = [a for a in articles if search_query.lower() in (a.get("title") or "").lower()]

    return JsonResponse({"status": "ok", "totalResults": len(articles), "articles": articles})

def get_trending_news(request):
    """Get trending news using popularity and recent timeframe"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    try:
        # Calculate date for last 3 days for trending topics
        from_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
        
        # Use everything endpoint with trending keywords and popularity sorting
        trending_keywords = "India trending OR viral OR popular OR breaking OR major"
        url = f"https://newsapi.org/v2/everything?q={trending_keywords}&language=en&from={from_date}&sortBy=popularity&pageSize=15&apiKey={api_key}"
        
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        # Filter out low-quality articles
        filtered_articles = []
        for article in articles:
            title = article.get("title", "")
            description = article.get("description", "")
            
            # Skip articles with these patterns
            if any(skip in title.lower() for skip in ['removed', 'deleted', '[removed]', 'untitled']):
                continue
            if not title or not description:
                continue
                
            filtered_articles.append(article)
        
        # Format for frontend
        trending_items = []
        for article in filtered_articles[:6]:
            trending_items.append({
                "title": article.get("title", ""),
                "description": article.get("description", "")[:100] + "..." if article.get("description") else "",
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", ""),
                "source": article.get("source", {}).get("name", ""),
                "urlToImage": article.get("urlToImage", "")
            })
        
        return JsonResponse({
            "status": "ok",
            "trending": trending_items
        })
    
    except requests.RequestException as e:
        return JsonResponse({"status": "error", "message": str(e)})


def get_recent_news(request):
    """Get recent news for sidebar"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    # Get top headlines from India
    url = f"https://newsapi.org/v2/top-headlines?country=in&pageSize=8&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        recent_items = []
        for article in articles[:6]:
            recent_items.append({
                "title": article.get("title", ""),
                "description": article.get("description", "")[:80] + "..." if article.get("description") else "",
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", ""),
                "source": article.get("source", {}).get("name", ""),
                "urlToImage": article.get("urlToImage", "")
            })
        
        return JsonResponse({
            "status": "ok",
            "recent": recent_items
        })
    
    except requests.RequestException as e:
        return JsonResponse({"status": "error", "message": str(e)})


def get_sidebar_data(request):
    """Combined endpoint for both trending and recent news with detailed logging"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    try:
        trending_items = []
        recent_items = []
        
        # ===== GET TRENDING NEWS =====
        try:
            from_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            trending_url = f"https://newsapi.org/v2/everything?q=India trending OR viral OR popular&language=en&from={from_date}&sortBy=popularity&pageSize=10&apiKey={api_key}"
            
            trending_response = requests.get(trending_url, timeout=10)
            trending_data = trending_response.json()
            
            if trending_data.get('status') == 'ok':
                trending_articles = trending_data.get("articles", [])
                
                for article in trending_articles[:6]:
                    title = article.get("title", "")
                    if title and not any(skip in title.lower() for skip in ['removed', 'deleted', '[removed]']):
                        trending_items.append({
                            "title": title,
                            "description": article.get("description", "")[:100] + "..." if article.get("description") else "No description available.",
                            "url": article.get("url", ""),
                            "publishedAt": article.get("publishedAt", ""),
                            "source": article.get("source", {}).get("name", "Unknown")
                        })
                        
        except Exception as e:
            print(f"Error fetching trending news: {str(e)}")
        
        # ===== GET RECENT NEWS =====
        try:
            recent_url = f"https://newsapi.org/v2/top-headlines?country=in&pageSize=10&apiKey={api_key}"
            
            recent_response = requests.get(recent_url, timeout=10)
            recent_data = recent_response.json()
            
            if recent_data.get('status') == 'ok':
                recent_articles = recent_data.get("articles", [])
                
                for article in recent_articles[:6]:
                    title = article.get("title", "")
                    if title and not any(skip in title.lower() for skip in ['removed', 'deleted', '[removed]']):
                        recent_items.append({
                            "title": title,
                            "description": article.get("description", "")[:80] + "..." if article.get("description") else "No description available.",
                            "url": article.get("url", ""),
                            "publishedAt": article.get("publishedAt", ""),
                            "source": article.get("source", {}).get("name", "Unknown")
                        })
                        
        except Exception as e:
            print(f"Error fetching recent news: {str(e)}")
        
        # ===== FALLBACK: If recent news is empty, try without country filter =====
        if not recent_items:
            try:
                fallback_url = f"https://newsapi.org/v2/top-headlines?language=en&pageSize=10&apiKey={api_key}"
                
                fallback_response = requests.get(fallback_url, timeout=10)
                fallback_data = fallback_response.json()
                
                if fallback_data.get('status') == 'ok':
                    fallback_articles = fallback_data.get("articles", [])
                    
                    for article in fallback_articles[:6]:
                        title = article.get("title", "")
                        if title and not any(skip in title.lower() for skip in ['removed', 'deleted', '[removed]']):
                            recent_items.append({
                                "title": title,
                                "description": article.get("description", "")[:80] + "..." if article.get("description") else "No description available.",
                                "url": article.get("url", ""),
                                "publishedAt": article.get("publishedAt", ""),
                                "source": article.get("source", {}).get("name", "Unknown")
                            })
                            
            except Exception as e:
                print(f"Fallback also failed: {str(e)}")
        
        # ===== RETURN RESPONSE =====
        return JsonResponse({
            "status": "ok",
            "sidebar": {
                "trending": trending_items,
                "recent": recent_items
            }
        })
        
    except Exception as e:
        print(f"Critical error in get_sidebar_data: {str(e)}")
        return JsonResponse({
            "status": "error", 
            "message": str(e),
            "sidebar": {
                "trending": [],
                "recent": []
            }
        })


def get_advanced_trending_news(request):
    """Advanced trending news with multiple strategies"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    try:
        all_trending = []
        
        # Strategy 1: Popular articles from last 2 days
        from_date = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
        popular_url = f"https://newsapi.org/v2/everything?language=en&from={from_date}&sortBy=popularity&pageSize=8&apiKey={api_key}"
        
        popular_response = requests.get(popular_url)
        popular_data = popular_response.json()
        popular_articles = popular_data.get("articles", [])[:4]
        
        # Strategy 2: Trending keywords
        trending_keywords = "trending OR viral OR breaking OR major OR important"
        keyword_url = f"https://newsapi.org/v2/everything?q={trending_keywords}&language=en&from={from_date}&sortBy=popularity&pageSize=6&apiKey={api_key}"
        
        keyword_response = requests.get(keyword_url)
        keyword_data = keyword_response.json()
        keyword_articles = keyword_data.get("articles", [])[:3]
        
        # Combine and remove duplicates
        all_articles = popular_articles + keyword_articles
        seen_urls = set()
        unique_articles = []
        
        for article in all_articles:
            url = article.get("url", "")
            title = article.get("title", "")
            
            if (url and url not in seen_urls and title and 
                not any(skip in title.lower() for skip in ['removed', 'deleted', '[removed]'])):
                seen_urls.add(url)
                unique_articles.append(article)
        
        # Format trending items
        trending_items = []
        for article in unique_articles[:6]:
            trending_items.append({
                "title": article.get("title", ""),
                "description": article.get("description", "")[:100] + "..." if article.get("description") else "",
                "url": article.get("url", ""),
                "publishedAt": article.get("publishedAt", ""),
                "source": article.get("source", {}).get("name", "")
            })
        
        return JsonResponse({
            "status": "ok",
            "trending": trending_items
        })
    
    except requests.RequestException as e:
        return JsonResponse({"status": "error", "message": str(e)})


def get_recent_news(request):
    """Get news from past 10 days for sidebar"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    # Calculate date 10 days ago
    ten_days_ago = (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d')
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get recent news from past 10 days
    url = f"https://newsapi.org/v2/everything?q=India&from={ten_days_ago}&to={today}&sortBy=publishedAt&language=en&pageSize=15&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        # Format for sidebar display
        recent_items = []
        for article in articles[:6]:  # Limit to 6 items for sidebar
            published_date = article.get("publishedAt", "")
            if published_date:
                # Parse and format date for better display
                try:
                    date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    formatted_date = date_obj.strftime('%b %d, %Y')
                except:
                    formatted_date = published_date[:10]  # Fallback to YYYY-MM-DD
            else:
                formatted_date = ""
            
            recent_items.append({
                "title": article.get("title", ""),
                "description": article.get("description", "")[:100] + "..." if article.get("description") else "",
                "url": article.get("url", ""),
                "publishedAt": formatted_date,
                "source": article.get("source", {}).get("name", "")
            })
        
        return JsonResponse({
            "status": "ok",
            "recent": recent_items
        })
        
    except requests.RequestException as e:
        return JsonResponse({"status": "error", "message": str(e)})


def process_news_query(user_message):
    """Process user message and return appropriate news response"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    # Intent detection patterns
    patterns = {
        'trending': ['trending', 'popular', 'hot', 'viral', 'top news'],
        'recent': ['recent', 'latest', 'today', 'new', 'fresh'],
        'sports': ['sports', 'cricket', 'football', 'match', 'game', 'player'],
        'politics': ['politics', 'government', 'election', 'minister', 'parliament'],
        'bollywood': ['bollywood', 'movie', 'actor', 'actress', 'film', 'celebrity'],
        'technology': ['technology', 'tech', 'gadget', 'innovation', 'ai', 'startup'],
        'business': ['business', 'economy', 'market', 'finance', 'stock', 'company'],
        'health': ['health', 'medical', 'doctor', 'hospital', 'covid', 'vaccine']
    }
    
    # Detect intent
    detected_intent = detect_intent(user_message, patterns)
    
    # Generate response based on intent
    if detected_intent == 'trending':
        return get_trending_response()
    elif detected_intent == 'recent':
        return get_recent_response()
    elif detected_intent in ['sports', 'politics', 'bollywood', 'technology', 'business', 'health']:
        return get_category_response(detected_intent)
    else:
        # General search or greeting
        if any(word in user_message for word in ['hello', 'hi', 'hey', 'help']):
            return get_help_response()
        else:
            return search_news_response(user_message)

def detect_intent(message, patterns):
    """Detect user intent based on keywords"""
    for intent, keywords in patterns.items():
        if any(keyword in message for keyword in keywords):
            return intent
    return 'general'

def get_trending_response():
    """Get trending news response"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    url = f"https://newsapi.org/v2/top-headlines?country=in&pageSize=5&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        if articles:
            bot_response = "🔥 Here are the top trending news stories:\n\n"
            for i, article in enumerate(articles[:3], 1):
                title = article.get("title", "")
                source = article.get("source", {}).get("name", "Unknown")
                bot_response += f"{i}. **{title}**\n   📰 Source: {source}\n\n"
            bot_response += "Would you like more details on any of these stories?"
        else:
            bot_response = "Sorry, I couldn't fetch trending news at the moment. Please try again later."
            
    except Exception as e:
        bot_response = "Sorry, there was an error fetching trending news. Please try again."
    
    return bot_response

def get_recent_response():
    """Get recent news response"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    today = datetime.now().strftime('%Y-%m-%d')
    url = f"https://newsapi.org/v2/everything?q=India&from={today}&sortBy=publishedAt&language=en&pageSize=5&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        if articles:
            bot_response = "⏰ Here are the latest news updates:\n\n"
            for i, article in enumerate(articles[:3], 1):
                title = article.get("title", "")
                published = article.get("publishedAt", "")
                if published:
                    try:
                        date_obj = datetime.fromisoformat(published.replace('Z', '+00:00'))
                        time_str = date_obj.strftime('%I:%M %p')
                    except:
                        time_str = "Recently"
                else:
                    time_str = "Recently"
                
                bot_response += f"{i}. **{title}**\n   🕒 {time_str}\n\n"
            bot_response += "Stay updated! Ask me about specific categories for more news."
        else:
            bot_response = "No recent news found. Try asking about trending news instead!"
            
    except Exception as e:
        bot_response = "Sorry, there was an error fetching recent news. Please try again."
    
    return bot_response

def get_category_response(category):
    """Get category-specific news response"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    category_queries = {
        'sports': 'India sports cricket football',
        'politics': 'India politics government',
        'bollywood': 'India bollywood entertainment',
        'technology': 'India technology gadgets',
        'business': 'India business economy',
        'health': 'India health medical'
    }
    
    category_emojis = {
        'sports': '⚽',
        'politics': '🏛️',
        'bollywood': '🎬',
        'technology': '💻',
        'business': '💼',
        'health': '🏥'
    }
    
    query = category_queries.get(category, f'India {category}')
    emoji = category_emojis.get(category, '📰')
    
    url = f"https://newsapi.org/v2/everything?q={query}&sortBy=publishedAt&language=en&pageSize=5&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        if articles:
            bot_response = f"{emoji} Here are the latest {category} news:\n\n"
            for i, article in enumerate(articles[:3], 1):
                title = article.get("title", "")
                source = article.get("source", {}).get("name", "Unknown")
                bot_response += f"{i}. **{title}**\n   📰 {source}\n\n"
            bot_response += f"Want more {category} news? Just ask!"
        else:
            bot_response = f"Sorry, no {category} news found at the moment. Try again later!"
            
    except Exception as e:
        bot_response = f"Sorry, there was an error fetching {category} news. Please try again."
    
    return bot_response

def search_news_response(query):
    """Search for news based on user query"""
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    search_query = f"India {query}"
    
    url = f"https://newsapi.org/v2/everything?q={search_query}&sortBy=relevancy&language=en&pageSize=5&apiKey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        articles = data.get("articles", [])
        
        if articles:
            bot_response = f"🔍 Here's what I found about '{query}':\n\n"
            for i, article in enumerate(articles[:3], 1):
                title = article.get("title", "")
                source = article.get("source", {}).get("name", "Unknown")
                bot_response += f"{i}. **{title}**\n   📰 {source}\n\n"
            bot_response += "Need more specific information? Try asking about categories like sports, politics, or technology."
        else:
            bot_response = f"Sorry, I couldn't find any news about '{query}'. Try asking about:\n• Trending news\n• Sports updates\n• Bollywood news\n• Technology news\n• Political updates"
            
    except Exception as e:
        bot_response = "Sorry, there was an error searching for news. Please try again."
    
    return bot_response

def get_help_response():
    """Provide help information"""
    return """👋 Hello! I'm your TrendLine News Assistant. Here's how I can help you:

**Ask me about:**
• "What's trending?" - Get top headlines
• "Latest news" - Recent updates
• "Sports news" - Cricket, football, and more
• "Bollywood news" - Entertainment updates
• "Technology news" - Tech and innovation
• "Political news" - Government updates
• "Business news" - Market and economy
• "Health news" - Medical updates

**Or simply ask:**
• "Tell me about [topic]" - I'll search for relevant news

What would you like to know about today? 📰"""


logger = logging.getLogger(__name__)


@login_required
def profile_view(request):
    """Display user profile page"""
    try:
        # Get or create user profile
        profile, created = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={
                'bio': '',
                'location': '',
                'timezone': 'UTC',
                'language': 'en',
                'email_notifications': True,
            }
        )
        
        if created:
            # Log activity when profile is created
            UserActivity.objects.create(
                user=request.user,
                activity_type='PROFILE_UPDATE',
                description='Profile automatically created',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            logger.info(f'New profile created for user {request.user.username}')
        
        context = {
            'title': 'TrendLine - My Profile',
            'profile': profile,
            'user': request.user,
        }
        
        return render(request, 'trendline/profile.html', context)
        
    except Exception as e:
        logger.error(f'Error in profile view for user {request.user.username}: {str(e)}')
        messages.error(request, 'Error loading profile data.')
        return redirect('dashboard')


@login_required
@require_http_methods(["GET"])
def get_profile_api(request):
    """API endpoint to get user profile data"""
    try:
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Prepare profile data
        profile_data = {
            'name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'phone_number': profile.phone_number or '',
            'bio': profile.bio or '',
            'website': profile.website or '',
            'location': profile.location or '',
            'birth_date': profile.birth_date.strftime('%Y-%m-%d') if profile.birth_date else '',
            'gender': profile.gender or '',
            'avatar_url': profile.get_avatar_url(),
            'email_notifications': profile.email_notifications,
            'sms_notifications': profile.sms_notifications,
            'marketing_emails': profile.marketing_emails,
        }
        
        return JsonResponse({
            'status': 'success',
            'profile': profile_data
        })
        
    except Exception as e:
        logger.error(f'Error getting profile data for user {request.user.username}: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'Error loading profile data'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_profile_api(request):
    """API endpoint to update user profile"""
    try:
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Parse JSON data
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
        
        # Update user fields
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
        if 'email' in data:
            user.email = data['email'].strip()
        
        # Update profile fields
        profile.phone_number = data.get('phone_number', profile.phone_number)
        profile.bio = data.get('bio', profile.bio)
        profile.website = data.get('website', profile.website)
        profile.location = data.get('location', profile.location)
        profile.gender = data.get('gender', profile.gender)
        
        # Handle birth_date
        if 'birth_date' in data and data['birth_date']:
            try:
                from datetime import datetime
                profile.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
            except ValueError:
                pass  # Keep existing birth_date if invalid format
        
        # Update notification preferences
        if 'email_notifications' in data:
            profile.email_notifications = bool(data['email_notifications'])
        if 'sms_notifications' in data:
            profile.sms_notifications = bool(data['sms_notifications'])
        if 'marketing_emails' in data:
            profile.marketing_emails = bool(data['marketing_emails'])
        
        # Save changes
        user.save()
        profile.save()
        
        # Log activity
        UserActivity.objects.create(
            user=user,
            activity_type='PROFILE_UPDATE',
            description='Profile updated via API',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={'update_method': 'api'}
        )
        
        logger.info(f'User {user.username} updated their profile via API')
        
        # Return updated profile data
        profile_data = {
            'name': f"{user.first_name} {user.last_name}".strip() or user.username,
            'email': user.email,
            'phone_number': profile.phone_number or '',
            'bio': profile.bio or '',
            'website': profile.website or '',
            'location': profile.location or '',
            'birth_date': profile.birth_date.strftime('%Y-%m-%d') if profile.birth_date else '',
            'gender': profile.gender or '',
            'avatar_url': profile.get_avatar_url(),
            'email_notifications': profile.email_notifications,
            'sms_notifications': profile.sms_notifications,
            'marketing_emails': profile.marketing_emails,
        }
        
        return JsonResponse({
            'status': 'success',
            'message': 'Profile updated successfully',
            'profile': profile_data
        })
        
    except Exception as e:
        logger.error(f'Error updating profile for user {request.user.username}: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'Error updating profile'
        }, status=500)


@login_required
@require_http_methods(["POST"])
def upload_avatar_api(request):
    """API endpoint to upload user avatar"""
    try:
        user = request.user
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        if 'avatar' not in request.FILES:
            return JsonResponse({
                'status': 'error',
                'message': 'No avatar file provided'
            }, status=400)
        
        avatar_file = request.FILES['avatar']
        
        # Validate file size (5MB limit)
        if avatar_file.size > 5 * 1024 * 1024:
            return JsonResponse({
                'status': 'error',
                'message': 'File size should be less than 5MB'
            }, status=400)
        
        # Validate file type
        if not avatar_file.content_type.startswith('image/'):
            return JsonResponse({
                'status': 'error',
                'message': 'Please select a valid image file'
            }, status=400)
        
        # Save the avatar
        profile.avatar = avatar_file
        profile.save()
        
        # Log activity
        UserActivity.objects.create(
            user=user,
            activity_type='PROFILE_UPDATE',
            description='Avatar uploaded',
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            metadata={'update_method': 'avatar_upload'}
        )
        
        logger.info(f'User {user.username} uploaded new avatar')
        
        return JsonResponse({
            'status': 'success',
            'message': 'Avatar uploaded successfully',
            'avatar_url': profile.get_avatar_url()
        })
        
    except Exception as e:
        logger.error(f'Error uploading avatar for user {request.user.username}: {str(e)}')
        return JsonResponse({
            'status': 'error',
            'message': 'Error uploading avatar'
        }, status=500)


def get_client_ip(request):
    """Helper function to get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_page_context(page_type):
    """Helper function to get page-specific context"""
    contexts = {
        'home': {
            'welcome_message': 'Welcome to TrendLine',
            'subtitle': 'Your Gateway to Success'
        },
        'register': {
            'side_message': 'Join TrendLine Today!',
            'side_subtitle': 'Create your account and start your journey with us.'
        },
        'login': {
            'side_message': 'Welcome Back!',
            'side_subtitle': 'Sign in to continue your TrendLine experience.'
        }
    }
    return contexts.get(page_type, {})


# Set up logging
logger = logging.getLogger(__name__)

class NewsChatView(View):
    """
    News Chat API View - handles chatbot queries
    """
    
    def __init__(self):
        super().__init__()
        self.api_key = "81509bdd2f3d4205bff00a258afce41b"
        self.base_url = "https://newsapi.org/v2/everything"
        self.top_headlines_url = "https://newsapi.org/v2/top-headlines"
    
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """Lightweight health response for chat endpoint checks."""
        return JsonResponse({
            'status': 'success',
            'message': 'Chat endpoint is reachable'
        })

    def head(self, request):
        """Support HEAD checks used by dashboard connection monitoring."""
        return HttpResponse(status=200)
    
    def post(self, request):
        try:
            # Parse the JSON request
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            
            logger.info(f"Received message: {user_message}")
            
            if not user_message:
                return JsonResponse({
                    'status': 'error',
                    'message': 'No message provided'
                })
            
            # Test API key first
            api_test_result = self.test_api_connection()
            if not api_test_result['success']:
                return JsonResponse({
                    'status': 'success',  # Changed to success to display message
                    'bot_response': f"🔧 **API Connection Issue**\n\n{api_test_result['error']}\n\nPlease check:\n• API key validity\n• Internet connection\n• News API service status"
                })
            
            # Generate response
            response = self.generate_news_response(user_message)
            
            return JsonResponse({
                'status': 'success',
                'bot_response': response
            })
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Invalid JSON data: {str(e)}'
            })
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'An error occurred: {str(e)}'
            })
    
    def test_api_connection(self):
        """
        Test the News API connection and return detailed results
        """
        try:
            logger.info(f"Testing API connection to: {self.top_headlines_url}")
            
            response = requests.get(
                self.top_headlines_url,
                params={
                    'country': 'us',
                    'pageSize': 1,
                    'apiKey': self.api_key
                },
                timeout=10
            )
            
            logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info(f"API Response Data Status: {data.get('status')}")
                
                if data.get('status') == 'ok':
                    return {'success': True}
                else:
                    return {
                        'success': False,
                        'error': f"API returned error: {data.get('message', 'Unknown error')}"
                    }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'error': "API key is invalid or expired. Please check your News API key."
                }
            elif response.status_code == 429:
                return {
                    'success': False,
                    'error': "API rate limit exceeded. Please try again later."
                }
            else:
                return {
                    'success': False,
                    'error': f"API returned status code {response.status_code}"
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': "Request timeout. News API is taking too long to respond."
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': "Connection error. Please check your internet connection."
            }
        except Exception as e:
            return {
                'success': False,
                'error': f"Unexpected error during API test: {str(e)}"
            }
    
    def generate_news_response(self, user_message):
        """
        Generate appropriate news response based on user message
        """
        message_lower = user_message.lower()
        
        logger.info(f"Processing message: {user_message}")
        
        # Handle greetings
        if any(word in message_lower for word in ['hello', 'hi', 'hey', 'help', 'start']):
            return ("👋 **Welcome to TrendLine News Chat!**\n\n"
                   "I can help you with:\n"
                   "• 🔥 Trending news\n"
                   "• ⚽ Sports updates\n"
                   "• 🎬 Bollywood gossip\n"
                   "• 💻 Tech news\n"
                   "• 💼 Business updates\n"
                   "• 🏥 Health news\n\n"
                   "Just ask me about any topic!")
        
        # Detect query intent
        if any(word in message_lower for word in ['trending', 'popular', 'hot', 'viral', 'today']):
            return self.get_trending_news()
        elif any(word in message_lower for word in ['sports', 'football', 'cricket', 'tennis', 'soccer']):
            return self.search_news('sports', category='sports')
        elif any(word in message_lower for word in ['bollywood', 'movies', 'entertainment', 'celebrity']):
            return self.search_news('bollywood entertainment', category='entertainment')
        elif any(word in message_lower for word in ['technology', 'tech', 'gadgets', 'ai', 'software']):
            return self.search_news('technology', category='technology')
        elif any(word in message_lower for word in ['business', 'finance', 'economy', 'market', 'stock']):
            return self.search_news('business', category='business')
        elif any(word in message_lower for word in ['health', 'medical', 'coronavirus', 'covid']):
            return self.search_news('health', category='health')
        elif any(word in message_lower for word in ['politics', 'election', 'government']):
            return self.search_news('politics')
        else:
            return self.search_news(user_message)
    
    def get_trending_news(self):
        """
        Fetch trending/top headlines
        """
        try:
            params = {
                'country': 'us',
                'pageSize': 5,
                'apiKey': self.api_key
            }
            
            logger.info(f"Fetching trending news with params: {params}")
            
            response = requests.get(self.top_headlines_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            logger.info(f"Response status: {data.get('status')}, articles: {len(data.get('articles', []))}")
            
            if data['status'] == 'ok' and data['articles']:
                return self.format_news_response(data['articles'], "🔥 **Trending News**")
            elif data['status'] == 'ok' and not data['articles']:
                return "📰 No trending articles found at the moment. Try searching for specific topics instead!"
            else:
                error_msg = data.get('message', 'Unknown API error')
                logger.error(f"API error: {error_msg}")
                return f"❌ **API Error**: {error_msg}"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return f"🔌 **Connection Error**: Could not fetch news. Please try again."
        except Exception as e:
            logger.error(f"Unexpected error in get_trending_news: {e}")
            return f"⚠️ **Unexpected Error**: {str(e)}"
    
    def search_news(self, query, category=None):
        """
        Search for specific news based on query
        """
        try:
            logger.info(f"Searching for: {query}, category: {category}")
            
            # Try top headlines first if category is specified
            if category:
                try:
                    headlines_params = {
                        'category': category,
                        'country': 'us',
                        'pageSize': 5,
                        'apiKey': self.api_key
                    }
                    
                    response = requests.get(self.top_headlines_url, params=headlines_params, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    
                    if data['status'] == 'ok' and data['articles']:
                        return self.format_news_response(data['articles'], f"📰 **{category.title()} News**")
                        
                except Exception as e:
                    logger.warning(f"Category search failed, falling back to general search: {e}")
            
            # General search fallback
            params = {
                'q': query,
                'sortBy': 'publishedAt',
                'pageSize': 5,
                'language': 'en',
                'apiKey': self.api_key
            }
            
            # Add date filter for recent news (last 30 days)
            month_ago = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            params['from'] = month_ago
            
            response = requests.get(self.base_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'ok' and data['articles']:
                return self.format_news_response(data['articles'], f"🔍 **Search Results for: {query}**")
            else:
                return f"🔍 **No Results Found**\n\nNo recent news found for '{query}'. Try different keywords!"
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Search request error: {e}")
            return f"🔌 **Search Error**: Could not fetch news. Please try again."
        except Exception as e:
            logger.error(f"Unexpected search error: {e}")
            return f"⚠️ **Search Error**: {str(e)}"
    
    def format_news_response(self, articles, header):
        """
        Format articles into a readable chat response
        """
        if not articles:
            return "📰 No news articles found."
        
        logger.info(f"Formatting {len(articles)} articles")
        
        response_parts = [header, ""]
        
        for i, article in enumerate(articles[:5], 1):
            title = article.get('title', 'No title')
            description = article.get('description', '')
            source = article.get('source', {}).get('name', 'Unknown source')
            published_at = article.get('publishedAt', '')
            url = article.get('url', '')
            
            # Skip articles with null/empty titles
            if not title or title == 'No title':
                continue
            
            # Format published date
            try:
                if published_at:
                    pub_date = datetime.strptime(published_at, '%Y-%m-%dT%H:%M:%SZ')
                    time_str = pub_date.strftime('%b %d, %I:%M %p')
                else:
                    time_str = 'Unknown time'
            except:
                time_str = 'Unknown time'
            
            # Clean title and description
            title = self.clean_text(title)
            description = self.clean_text(description) if description else "Click to read more..."
            
            # Truncate description if too long
            if len(description) > 120:
                description = description[:117] + "..."
            
            article_text = f"**{i}. {title}**\n"
            article_text += f"📰 {source} • ⏰ {time_str}\n"
            article_text += f"{description}\n"
            
            if url:
                article_text += f"🔗 [Read full article]({url})\n"
            
            response_parts.append(article_text)
        
        if len(response_parts) <= 2:
            return "📰 No valid articles found in the results."
        
        response_parts.append("\n💡 *Try asking about specific topics like 'tech news', 'sports updates', or 'business news'!*")
        
        return "\n".join(response_parts)
    
    def clean_text(self, text):
        """
        Clean and sanitize text for display
        """
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Remove or replace problematic characters
        text = text.replace('\u2019', "'").replace('\u2018', "'")
        text = text.replace('\u201c', '"').replace('\u201d', '"')
        text = text.replace('\u2013', '-').replace('\u2014', '-')
        
        return text


# Test view to check API directly
@csrf_exempt
@require_http_methods(["GET"])
def test_api_view(request):
    """
    Direct API test endpoint - access at /api/test/
    """
    api_key = "81509bdd2f3d4205bff00a258afce41b"
    
    try:
        response = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={
                'country': 'us',
                'pageSize': 3,
                'apiKey': api_key
            },
            timeout=10
        )
        
        return JsonResponse({
            'status_code': response.status_code,
            'response': response.json() if response.status_code == 200 else response.text[:500],
        })
        
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        })
        
