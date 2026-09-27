from django.contrib import admin
from django.urls import path
from trader import views

urlpatterns = [path("admin/", admin.site.urls), path("oauth/callback", views.oauth_callback, name="oauth_callback"), path("pay/<str:token>/", views.payment_page, name="payment_page"), path("healthz", views.healthz)]

