from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm, AuthenticationForm
from django.contrib.auth import authenticate
from .models import UserProfile, LoginSession, UserActivity, ChatConversation, ChatMessage


class UserProfileForm(forms.ModelForm):
    """Form for UserProfile model"""
    
    class Meta:
        model = UserProfile
        fields = [
            'phone_number', 'alternate_email', 'bio', 'location', 
            'birth_date', 'gender', 'avatar', 'cover_image',
            'website', 'linkedin', 'twitter', 'github',
            'timezone', 'language',
            'show_email', 'show_phone', 'show_birth_date',
            'email_notifications', 'sms_notifications', 'marketing_emails'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter phone number'
            }),
            'alternate_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter alternate email'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about yourself...'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City, Country'
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'avatar': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'cover_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://yourwebsite.com'
            }),
            'linkedin': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/username'
            }),
            'twitter': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/username'
            }),
            'github': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/username'
            }),
            'timezone': forms.Select(attrs={
                'class': 'form-control'
            }),
            'language': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }
        
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise forms.ValidationError('Please enter a valid phone number.')
        return phone


class CustomUserCreationForm(UserCreationForm):
    """Custom form for creating users with additional fields"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class CustomAuthenticationForm(AuthenticationForm):
    """Custom authentication form that allows login with username or email"""
    
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )
    
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate with username first
            self.user_cache = authenticate(
                self.request, 
                username=username, 
                password=password
            )
            
            # If that fails, try with email
            if self.user_cache is None:
                try:
                    user = User.objects.get(email=username)
                    self.user_cache = authenticate(
                        self.request,
                        username=user.username,
                        password=password
                    )
                except User.DoesNotExist:
                    pass
            
            if self.user_cache is None:
                raise forms.ValidationError(
                    "Invalid username/email or password.",
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return self.cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')
        if commit:
            user.save()
        return user


class CustomUserChangeForm(UserChangeForm):
    """Custom form for updating user information"""
    
    password = None  # Remove password field from the form
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'is_active', 'is_staff')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': 'readonly'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }


class LoginSessionForm(forms.ModelForm):
    """Form for LoginSession model"""
    
    class Meta:
        model = LoginSession
        fields = ['user', 'ip_address', 'user_agent', 'country', 'city', 'is_active']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'ip_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '192.168.1.1'
            }),
            'user_agent': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Country'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City'
            }),
        }


class UserActivityForm(forms.ModelForm):
    """Form for UserActivity model"""
    
    class Meta:
        model = UserActivity
        fields = ['user', 'activity_type', 'description', 'ip_address', 'user_agent', 'metadata']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'activity_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Activity description...'
            }),
            'ip_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '192.168.1.1'
            }),
            'user_agent': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2
            }),
            'metadata': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '{"key": "value"}'
            }),
        }


class ChatConversationForm(forms.ModelForm):
    """Form for ChatConversation model"""
    
    class Meta:
        model = ChatConversation
        fields = ['user', 'session_id']
        widgets = {
            'user': forms.Select(attrs={
                'class': 'form-control'
            }),
            'session_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Session ID for anonymous users'
            }),
        }


class ChatMessageForm(forms.ModelForm):
    """Form for ChatMessage model"""
    
    class Meta:
        model = ChatMessage
        fields = ['conversation', 'message_type', 'content']
        widgets = {
            'conversation': forms.Select(attrs={
                'class': 'form-control'
            }),
            'message_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Message content...'
            }),
        }


class UserFilterForm(forms.Form):
    """Form for filtering users in admin panel"""
    
    username = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by username'
        })
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by email'
        })
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    is_staff = forms.ChoiceField(
        required=False,
        choices=[('', 'All'), ('true', 'Staff'), ('false', 'Non-Staff')],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    date_joined_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_joined_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )


class BulkUserActionForm(forms.Form):
    """Form for bulk actions on users"""
    
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('activate', 'Activate Users'),
        ('deactivate', 'Deactivate Users'),
        ('delete', 'Delete Users'),
        ('send_email', 'Send Email'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    user_ids = forms.CharField(
        widget=forms.HiddenInput()
    )