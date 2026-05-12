from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect


def redirect_by_role(user):
    if user.is_superuser:
        return redirect('admin_dashboard')
    elif user.role == 'sales':
        return redirect('sales_dashboard')
    elif user.role == 'campaign':
        return redirect('campaign_dashboard')
    elif user.role == 'marketing':
        return redirect('marketing_dashboard')
    elif user.role == 'admin':
        return redirect('admin_dashboard')

    return redirect('login')


def login_view(request):
    if request.user.is_authenticated:
        return redirect_by_role(request.user)

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, email=email, password=password)

        if user is not None:
            login(request, user)
            return redirect_by_role(user)

        return render(request, 'accounts/login.html', {
            'error': 'Invalid email or password'
        })

    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')