from datetime import timedelta


from django.utils import timezone


from rest_framework import mixins, viewsets, exceptions, status
from rest_framework.decorators import action
from rest_framework.response import Response


from ticket.models import Event, TicketType, Order
from ticket.serializers import EventSerializer, TicketTypeSerializer, OrderSerializer


class EventViewSet(viewsets.ModelViewSet, viewsets.ReadOnlyModelViewSet):
    serializer_class = EventSerializer
    queryset = Event.objects.prefetch_related("ticket_types")
    permission_classes = ()

    @action(methods=['GET'], detail=True, permission_classes=permission_classes)
    def get_count_orders(self, request, *args, **kwargs):
        event = self.get_object()
        orders = Order.objects.filter(ticket_type__event=event).distinct()
        count_orders = orders.count()
        cancellation_rate = (orders.filter(cancelled=True).count()/count_orders) * 100
        data = {
            "count_orders": count_orders,
            "cancellation_rate": cancellation_rate
        }
        return Response(data)


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

    @action(methods=['GET'], detail=False, permission_classes=permission_classes)
    def get_date_highest_cancellations(self, request, *args, **kwargs):
        highest_cancellations = Order.get_date_highest_cancellations()
        data = {
            'date': highest_cancellations['date_cancelled'],
            'number_of_cancellations': highest_cancellations['cancelled_ticket_sum']
        }
        return Response(data)

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
            return Response(data, status=status.HTTP_400_BAD_REQUEST)

        order.cancelled = True
        order.cancelled_at = now
        order.save()
        order.release_tickets()
        data = {'msg': 'Order has been successfully cancelled'}

        return Response(data)
