from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('upload/', views.upload, name='upload'),
    path('demo/', views.demo, name='demo'),
    path('sample.csv', views.sample_csv, name='sample_csv'),
    path('d/<int:dataset_id>/', views.dashboard, name='dashboard'),
    path('d/<int:dataset_id>/recommend/', views.recommend, name='recommend'),
]
