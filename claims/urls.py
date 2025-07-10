from django.urls import path
from . import views

app_name = 'claims'

urlpatterns = [
    # Main claim views
    path('', views.claim_list, name='claim_list'),
    path('create/', views.claim_create, name='claim_create'),
    path('<uuid:pk>/', views.claim_detail, name='claim_detail'),
    path('<uuid:pk>/update/', views.claim_update, name='claim_update'),
    path('<uuid:pk>/delete/', views.claim_delete, name='claim_delete'),
    
    # Upload and mapping views
    path('<uuid:claim_id>/upload/', views.upload_data, name='upload_data'),
    path('<uuid:claim_id>/mapping/', views.column_mapping, name='column_mapping'),
    path('<uuid:claim_id>/processing/', views.process_claim, name='process_claim'),
    
    # Results and export views
    path('<uuid:claim_id>/results/', views.claim_results, name='claim_results'),
    path('<uuid:claim_id>/narrative/', views.claim_narrative, name='claim_narrative'),
    path('<uuid:claim_id>/export/', views.export_claim, name='export_claim'),
    
    # Cost category detail view
    path('<uuid:claim_id>/category/<uuid:category_id>/', views.cost_category_detail, name='cost_category_detail'),
    
    # Employee management
    path('<uuid:claim_id>/employees/', views.employee_list, name='employee_list'),
    path('<uuid:claim_id>/employees/add/', views.employee_add, name='employee_add'),
    path('<uuid:claim_id>/employees/<uuid:employee_id>/edit/', views.employee_edit, name='employee_edit'),
    
    # Mapping templates (these might still use integer IDs if they're not UUIDs)
    path('mappings/', views.mapping_list, name='mapping_list'),
    path('mappings/create/', views.mapping_create, name='mapping_create'),
    path('mappings/<int:pk>/', views.mapping_detail, name='mapping_detail'),
    path('mappings/<int:pk>/update/', views.mapping_update, name='mapping_update'),
    path('mappings/<int:pk>/delete/', views.mapping_delete, name='mapping_delete'),
    
    # AJAX endpoint for saving mappings
    path('<uuid:claim_id>/save_mapping/', views.save_mapping, name='save_mapping'),
] 