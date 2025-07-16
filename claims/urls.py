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
    
    # Generic line item management
    path('<uuid:claim_id>/items/', views.line_item_list, name='line_item_list'),
    path('<uuid:claim_id>/items/<str:category_type>/', views.line_item_list, name='line_item_list_by_category'),
    path('<uuid:claim_id>/items/add/', views.line_item_add, name='line_item_add'),
    path('<uuid:claim_id>/items/add/<str:category_type>/', views.line_item_add, name='line_item_add_by_category'),
    path('<uuid:claim_id>/items/<uuid:item_id>/edit/', views.line_item_edit, name='line_item_edit'),
    path('<uuid:claim_id>/items/<uuid:item_id>/delete/', views.line_item_delete, name='line_item_delete'),
    
    # Mapping templates (these might still use integer IDs if they're not UUIDs)
    path('mappings/', views.mapping_list, name='mapping_list'),
    path('mappings/create/', views.mapping_create, name='mapping_create'),
    path('mappings/<int:pk>/', views.mapping_detail, name='mapping_detail'),
    path('mappings/<int:pk>/update/', views.mapping_update, name='mapping_update'),
    path('mappings/<int:pk>/delete/', views.mapping_delete, name='mapping_delete'),
    
    # AJAX endpoint for saving mappings
    path('<uuid:claim_id>/save_mapping/', views.save_mapping, name='save_mapping'),
    
    # Debug endpoints
    path('<uuid:claim_id>/debug-line-items/', views.debug_line_items, name='debug_line_items'),
] 