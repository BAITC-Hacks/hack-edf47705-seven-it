from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse, reverse_lazy


class CustomerLoginForm(AuthenticationForm):
    username = forms.CharField(label='Email или логин', widget=forms.TextInput(attrs={
        'autocomplete': 'username', 'placeholder': 'you@example.com', 'autofocus': True,
    }))
    password = forms.CharField(label='Пароль', strip=False, widget=forms.PasswordInput(attrs={
        'autocomplete': 'current-password',
    }))

    def clean(self):
        email = self.cleaned_data.get('username')
        if email:
            users = list(get_user_model().objects.filter(email__iexact=email)[:2])
            if not users and '@' not in email:
                users = list(get_user_model().objects.filter(username=email)[:2])
            if len(users) != 1:
                raise self.get_invalid_login_error()
            self.cleaned_data['username'] = users[0].get_username()
        return super().clean()

    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if user.is_staff or user.is_superuser:
            raise forms.ValidationError('Для аккаунта администратора используйте отдельный вход «Админ».', code='admin_account')


class CustomerLoginView(LoginView):
    template_name = 'forecast/accounts/login.html'
    authentication_form = CustomerLoginForm
    redirect_authenticated_user = True
    next_page = reverse_lazy('account')

    def get_success_url(self):
        # Always land in the customer's own account, never in /admin/ or an
        # arbitrary next URL passed to the public login form.
        return reverse('account')


class CustomerLogoutView(LogoutView):
    next_page = reverse_lazy('index')


@login_required
def account(request):
    from market.models import Profile

    names = set(request.user.groups.values_list('name', flat=True))
    roles = [label for name, label in [('Продавцы', 'Продавец'), ('Покупатели', 'Покупатель')] if name in names]
    profile = Profile.objects.filter(user=request.user).first()
    if profile:
        roles = [profile.get_role_display()]
    return render(request, 'forecast/accounts/account.html', {'account_roles': roles})
