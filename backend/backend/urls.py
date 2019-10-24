"""api URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
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
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from fuskar import views
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'students', views.StudentViewSet)
router.register(r'images', views.ImageViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'lectures', views.LectureViewSet)
# router.register(r'video', views.get_stream)
# router.register(r'contracts', views.ContractViewSet)
# router.register(r'maintenance_activity', views.MaintenanceActivityViewSet)
# router.register(r'equipments', views.EquipmentViewSet)
# router.register(r'equipment_types', views.EquipmentTypeViewSet)
# router.register(r'employees/location_history', views.LocationHistoryViewSet)
# router.register(r'employees', views.EmployeeViewSet)
# router.register(r'designations', views.DesignationViewSet)


urlpatterns = [
    path('video', views.get_stream),
    path('', include(router.urls)),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
  urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)