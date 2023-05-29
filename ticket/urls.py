from django.conf import settings


from rest_framework.routers import SimpleRouter
from rest_framework.routers import DefaultRouter
from ticket import viewsets


router = SimpleRouter(trailing_slash=False)
if settings.DEBUG:
    router = DefaultRouter()

router.register(r"events", viewsets.EventViewSet)
router.register(r"tickettypes", viewsets.TicketTypeViewset)
router.register(r"orders", viewsets.OrderViewSet)

urlpatterns = router.urls
