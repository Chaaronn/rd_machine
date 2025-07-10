from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

def login_view(request):
    """User login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    context = {
        'title': 'Login',
        'form': form,
    }
    return render(request, 'users/login.html', context)

def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')

def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreationForm()
    
    context = {
        'title': 'Register',
        'form': form,
    }
    return render(request, 'users/register.html', context)

@login_required
def profile_view(request):
    """User profile view"""
    context = {
        'title': 'Profile',
        'user': request.user,
    }
    return render(request, 'users/profile.html', context)

@login_required
def edit_profile_view(request):
    """Edit user profile view"""
    if request.method == 'POST':
        # This would normally handle profile updates
        messages.success(request, 'Profile updated successfully!')
        return redirect('users:profile')
    
    context = {
        'title': 'Edit Profile',
        'user': request.user,
    }
    return render(request, 'users/edit_profile.html', context)
