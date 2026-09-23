from .models import Profile


def account_context(request):
    role = None
    if request.user.is_authenticated:
        role = Profile.objects.filter(user=request.user).values_list('role', flat=True).first() or 'buyer'
    return {'account_role': role, 'account_is_seller': role == 'seller' or request.user.is_staff}
