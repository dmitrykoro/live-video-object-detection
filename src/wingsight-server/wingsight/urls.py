"""
URL configuration for wingsight project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

from stream_handler.views import AddStreamView
# from stream_handler.views import AddUserView
from stream_handler.views import AddUserWithIdView
from stream_handler.views import GetAllUserStreamSubscriptionsView
from stream_handler.views import ToggleStreamNotificationView
from stream_handler.views import DeactivateStreamSubscriptionView
from stream_handler.views import ReactivateStreamSubscriptionView
from stream_handler.views import DeleteStreamSubscriptionView
from stream_handler.views import ManageSNSSubscriptionView
from stream_handler.views import GetAllStreamSubscriptionRecognitionEntriesView
from stream_handler.views import UpdateStreamSubscriptionTargetSpeciesView


# swagger
schema_view = get_schema_view(
    openapi.Info(
        title="Wingsight API",
        default_version="v1",
        description="API documentation for Wingsight backend",
        contact=openapi.Contact(email="dk9148@rit.edu"),
        license=openapi.License(name="MIT License"),
    ),
    public=True,
)


urlpatterns = [
    # django built-in
    path('admin/', admin.site.urls),

    # WingSight API
    path('v1/add_stream', AddStreamView.as_view(), name='add_stream'),
    # path('v1/add_user', AddUserView.as_view(), name='add_user'),
    path('v1/add_user_with_id', AddUserWithIdView.as_view(), name='add_user_with_id'),
    path('v1/get_stream_subscriptions', GetAllUserStreamSubscriptionsView.as_view(), name='get_stream_subscriptions'),

    path('v1/deactivate_stream_subscription', DeactivateStreamSubscriptionView.as_view(), name='deactivate_stream_subscription'),
    path('v1/reactivate_stream_subscription', ReactivateStreamSubscriptionView.as_view(), name='reactivate_stream_subscription'),
    path('v1/delete_stream_subscription', DeleteStreamSubscriptionView.as_view(), name='delete_stream_subscription'),

    path('v1/get_all_stream_subscription_recognitions', GetAllStreamSubscriptionRecognitionEntriesView.as_view(), name='get_all_stream_subscription_recognitions'),
    path('v1/update_target_species', UpdateStreamSubscriptionTargetSpeciesView.as_view(), name='update_target_species'),
    # New SNS endpoints
    path('v1/manage_subscription', ManageSNSSubscriptionView.as_view(), name='manage_subscription'),
    path('v1/toggle_stream_notification', ToggleStreamNotificationView.as_view(), name='toggle_stream_notification'),

    # swagger
    re_path(r"^swagger(?P<format>\.json|\.yaml)$", schema_view.without_ui(cache_timeout=0), name="schema-json"),
    path("swagger/", schema_view.with_ui("swagger", cache_timeout=0), name="schema-swagger-ui"),
    path("redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    
]
