from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import render


# Custom decorator to restrict access based on user roles
def role_required(allowed_roles):

    # This decorator wraps the original view function
    def decorator(view_func):

        # Ensures the user is logged in before checking roles
        @login_required

        # Preserves the original function's metadata (name, docstring, etc.)
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # Allow access if:
            # 1. The user is a superuser (full access), OR
            # 2. The user's role is in the allowed_roles list
            if request.user.is_superuser or request.user.role in allowed_roles:
                return view_func(request, *args, **kwargs)

            # If access is denied, render a custom 403 page
            return render(request, 'dashboard/access_denied.html', status=403)

        return wrapper  # Return the wrapped function

    return decorator  # Return the decorator itself