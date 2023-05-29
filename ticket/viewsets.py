from datetime import timedelta


from django.utils import timezone
from django.db.models import Sum


from rest_framework import mixins, viewsets, exceptions
from rest_framework.decorators import action
from rest_framework.response import Response


from ticket.models import Event, TicketType, Order
from ticket.serializers import EventSerializer, TicketTypeSerializer, OrderSerializer


class EventViewSet(viewsets.ModelViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.prefetch_related("ticket_types")


class TicketTypeViewset(mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = TicketTypeSerializer
    queryset = TicketType.objects.prefetch_related("tickets")


class OrderViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    queryset = Order.objects.all()
    permission_classes = ()


    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(user=self.request.user)

    def perform_create(self, serializer):
        order = serializer.save(user=self.request.user)
        order.book_tickets()
        if not order.fulfilled:
            order.delete()
            raise exceptions.ValidationError("Couldn't book tickets")

    @action(methods=['POST'], detail=True, permission_classes=permission_classes)
    def cancel_order(self, request, *args, **kwargs):
        order = self.get_object()
        now = timezone.now()
        if order.created_at < now - timedelta(minutes=60):
            data = {
                'msg': 'Orders older than 30 minutes can not be cancelled'
            }
            return Response(data)

        order.cancelled = True
        order.cancelled_at = now
        order.save()
        order.release_tickets()
        data = {'msg': 'Order has been successfully cancelled'}

        return Response(data)
