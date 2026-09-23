from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class AccountTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'Test-only-Passphrase-728!'
        cls.seller = User.objects.create_user('seller@example.com', 'seller@example.com', cls.password)
        cls.buyer = User.objects.create_user('buyer@example.com', 'buyer@example.com', cls.password)
        cls.admin = User.objects.create_superuser('administrator', 'admin@example.com', cls.password)
        cls.seller.groups.add(Group.objects.create(name='Продавцы'))
        cls.buyer.groups.add(Group.objects.create(name='Покупатели'))

    def public_login(self, email):
        return self.client.post(reverse('login'), {'username': email, 'password': self.password})

    def admin_login(self):
        return self.client.post(reverse('admin:login'), {
            'username': self.admin.username, 'password': self.password, 'next': reverse('admin:index'),
        })

    def test_seller_and_buyer_can_login_and_see_only_own_profile(self):
        for user, role in [(self.seller, 'Продавец'), (self.buyer, 'Покупатель')]:
            with self.subTest(role=role):
                self.assertRedirects(self.public_login(user.email.upper()), reverse('account'))
                response = self.client.get(reverse('account'))
                self.assertContains(response, role)
                self.assertContains(response, user.email)
                other = self.buyer if user == self.seller else self.seller
                self.assertNotContains(response, other.email)
                self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)
                self.assertRedirects(self.client.post(reverse('logout')), reverse('index'))
                self.assertEqual(self.client.get(reverse('account')).status_code, 302)

    def test_admin_and_public_sessions_coexist_and_logout_independently(self):
        self.assertEqual(self.admin_login().status_code, 302)
        admin_key = self.client.cookies[settings.ADMIN_SESSION_COOKIE_NAME].value
        self.assertEqual(self.client.cookies[settings.ADMIN_SESSION_COOKIE_NAME]['path'], '/admin/')
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)
        self.assertNotContains(self.client.get(reverse('index')), self.admin.email)
        self.assertRedirects(self.public_login(self.seller.email), reverse('account'))
        self.assertNotEqual(admin_key, self.client.cookies[settings.SESSION_COOKIE_NAME].value)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertContains(self.client.get(reverse('account')), self.seller.email)
        self.client.post(reverse('logout'))
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 200)
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)
        self.public_login(self.buyer.email)
        self.client.post(reverse('admin:logout'))
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)
        self.assertContains(self.client.get(reverse('account')), self.buyer.email)

    def test_admin_credentials_rejected_by_public_login(self):
        for route in ('login', 'market:login'):
            response = self.client.post(reverse(route), {'username': self.admin.email, 'password': self.password})
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'отдельный вход')
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)

    def test_marketplace_username_login_and_role_access(self):
        from market.models import Profile

        seller = User.objects.create_user('registered-seller', password=self.password)
        Profile.objects.create(user=seller, role=Profile.Role.SELLER)
        response = self.client.post(reverse('market:login'), {'username': seller.username, 'password': self.password})
        self.assertRedirects(response, reverse('account'))
        self.assertEqual(self.client.get(reverse('market:seller')).status_code, 200)
        self.assertContains(self.client.get(reverse('account')), 'Продавец')
        self.client.post(reverse('logout'))
        Profile.objects.create(user=self.buyer, role=Profile.Role.BUYER)
        self.public_login(self.buyer.email)
        self.assertEqual(self.client.get(reverse('market:seller')).status_code, 403)

    def test_staff_cookie_cannot_be_used_as_customer_session(self):
        self.admin_login()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = self.client.cookies[settings.ADMIN_SESSION_COOKIE_NAME].value
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)
        self.assertNotContains(self.client.get(reverse('index')), self.admin.email)

    def test_regular_user_cannot_login_to_admin(self):
        response = self.client.post(reverse('admin:login'), {
            'username': self.buyer.username, 'password': self.password, 'next': reverse('admin:index'),
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)

    def test_inactive_and_incorrect_credentials_are_rejected(self):
        self.seller.is_active = False
        self.seller.save(update_fields=['is_active'])
        self.assertEqual(self.public_login(self.seller.email).status_code, 200)
        self.assertEqual(self.public_login('unknown@example.com').status_code, 200)
        self.assertEqual(self.client.post(reverse('login'), {'username': self.buyer.email, 'password': 'wrong'}).status_code, 200)
        self.assertEqual(self.client.get(reverse('account')).status_code, 302)

    def test_public_login_does_not_redirect_into_admin_or_external_site(self):
        response = self.client.post(reverse('login') + '?next=https://example.com/', {
            'username': self.buyer.email, 'password': self.password, 'next': '/admin/',
        })
        self.assertRedirects(response, reverse('account'))

    def test_csrf_required_and_logout_is_post_only(self):
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse('login'), {'username': self.buyer.email, 'password': self.password}).status_code, 403)
        self.public_login(self.buyer.email)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertEqual(client.post(reverse('logout')).status_code, 403)

    def test_accounts_visible_in_admin_user_list_by_role(self):
        self.admin_login()
        response = self.client.get(reverse('admin:auth_user_changelist'))
        self.assertContains(response, self.seller.email)
        self.assertContains(response, self.buyer.email)
        group = self.seller.groups.get()
        response = self.client.get(reverse('admin:auth_user_changelist'), {'groups__id__exact': group.pk})
        self.assertContains(response, self.seller.email)
        self.assertNotContains(response, self.buyer.email)
