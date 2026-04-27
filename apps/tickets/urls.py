"""
工单系统URL配置
"""
from django.urls import path
from . import views

app_name = 'tickets'

urlpatterns = [
    # 工单列表
    path('', views.TicketListView.as_view(), name='ticket_list'),
    path('my/', views.MyTicketsView.as_view(), name='my_tickets'),
    path('pending/', views.PendingTicketsView.as_view(), name='pending_tickets'),
    
    # 工单CRUD
    path('create/', views.TicketCreateView.as_view(), name='ticket_create'),
    path('<int:pk>/', views.TicketDetailView.as_view(), name='ticket_detail'),
    
    # 工单操作
    path('<int:pk>/assign/', views.ticket_assign, name='ticket_assign'),
    path('<int:pk>/status/', views.ticket_status_update, name='ticket_status_update'),
    path('<int:pk>/close/', views.ticket_close, name='ticket_close'),
    path('<int:pk>/comment/', views.ticket_comment, name='ticket_comment'),
    
    # 仪表盘
    path('dashboard/', views.TicketDashboardView.as_view(), name='dashboard'),
]
