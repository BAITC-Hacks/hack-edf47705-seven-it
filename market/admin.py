from django.contrib import admin
from .models import Observation, Product, Profile, Review


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['title', 'kind', 'seller', 'price', 'stock', 'is_demo', 'is_reference', 'is_published']
    list_filter = ['kind', 'is_published', 'is_demo', 'is_reference']
    search_fields = ['title', 'region', 'seller__username']
    list_select_related = ['seller']
    readonly_fields = ['demo_key', 'photo_key', 'brief']

    def get_readonly_fields(self, request, obj=None):
        fields = super().get_readonly_fields(request, obj)
        return fields if request.user.is_superuser else [*fields, 'seller']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'author', 'rating', 'is_hidden', 'created_at']
    list_filter = ['is_hidden', 'rating']
    search_fields = ['product__title', 'author__username', 'comment']
    readonly_fields = ['product', 'author', 'rating', 'comment', 'created_at', 'updated_at']
    fields = ['product', 'author', 'rating', 'comment', 'is_hidden', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        return False


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'role']
    list_filter = ['role']
    readonly_fields = ['user']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser and super().has_change_permission(request, obj)


@admin.register(Observation)
class ObservationAdmin(admin.ModelAdmin):
    list_display = ['product', 'date', 'price', 'sold']
    list_filter = ['date']
    search_fields = ['product__title']
    readonly_fields = ['product', 'date', 'price', 'sold']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

# Personal ledgers and support conversations are intentionally accessed only through owner-scoped views.
