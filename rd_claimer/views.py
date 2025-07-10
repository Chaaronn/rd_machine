from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home(request):
    """Home page view with dashboard stats for authenticated users"""
    context = {
        'title': 'Home',
    }
    
    # Add dashboard stats if user is authenticated
    if request.user.is_authenticated:
        # These would normally come from the database
        context.update({
            'stats': {
                'total_claims': 0,
                'in_progress': 0,
                'completed': 0,
                'total_credits': 0,
            }
        })
    
    return render(request, 'home.html', context) 