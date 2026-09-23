from forecast.account_views import CustomerLoginView, CustomerLogoutView
from django.urls import path
from . import views

app_name = 'market'
urlpatterns = [
    path('', views.catalog, name='catalog'),
    path('register/', views.register, name='register'),
    path('login/', CustomerLoginView.as_view(), name='login'),
    path('logout/', CustomerLogoutView.as_view(), name='logout'),
    path('products/<int:pk>/', views.product_detail, name='product'),
    path('products/<int:pk>/favorite/', views.favorite, name='favorite'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/history/', views.observation_edit, name='observation'),
    path('products/<int:pk>/import/', views.history_import, name='history_import'),
    path('products/<int:pk>/excel/', views.product_excel, name='product_excel'),
    path('seller/', views.seller_products, name='seller'),
    path('seller/new/', views.product_edit, name='product_create'),
    path('finances/', views.ledger, name='ledger'),
    path('finances/<int:pk>/archive/', views.ledger_archive, name='ledger_archive'),
    path('finances/<int:pk>/edit/', views.ledger_edit, name='ledger_edit'),
    path('finances/excel/', views.ledger_excel, name='ledger_excel'),
    path('support/', views.support, name='support'),
]
