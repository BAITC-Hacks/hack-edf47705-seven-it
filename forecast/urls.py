from django.urls import path

from . import views
from .account_views import CustomerLoginView, CustomerLogoutView, account

urlpatterns = [
    path('login/', CustomerLoginView.as_view(), name='login'),
    path('logout/', CustomerLogoutView.as_view(), name='logout'),
    path('account/', account, name='account'),
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('demo/', views.demo, name='demo'),
    path('sample.csv', views.sample_csv, name='sample_csv'),
    path('d/<int:dataset_id>/', views.dashboard, name='dashboard'),
    path('d/<int:dataset_id>/recommend/', views.recommend, name='recommend'),
]
