from django.contrib.auth import logout
from django.shortcuts import redirect

def custom_logout(request):
    """
    Custom logout view that handles both GET and POST requests cleanly,
    flushing the session and redirecting the user back to the login page.
    """
    logout(request)
    return redirect('login')