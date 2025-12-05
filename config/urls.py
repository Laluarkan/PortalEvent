from django.contrib import admin
from django.urls import path, include # Jangan lupa import include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # URL untuk Login Google (Otomatis dibuatkan allauth)
    # Ini akan membuat rute: /accounts/google/login/, /accounts/logout/, dll
    path('accounts/', include('allauth.urls')), 
    
    # URL Aplikasi Kita
    path('', include('events.urls')), # Saya asumsikan events punya urls.py sendiri
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)