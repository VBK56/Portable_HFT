# investments/api/serializers.py

from rest_framework import serializers
from ..models import Project, Transaction

class TransactionSerializer(serializers.ModelSerializer):
    """Сериализатор для транзакций"""
    investment_usd = serializers.ReadOnlyField()
    return_usd = serializers.ReadOnlyField()
    equity_usd = serializers.ReadOnlyField()
    nav_usd = serializers.ReadOnlyField()
    
    class Meta:
        model = Transaction
        fields = [
            'id', 'project', 'date', 'transaction_type',
            'investment', 'return_amount', 'equity', 'nav', 'x_rate',
            'investment_usd', 'return_usd', 'equity_usd', 'nav_usd'
        ]

class ProjectSerializer(serializers.ModelSerializer):
    """Сериализатор для проектов"""
    total_invested = serializers.ReadOnlyField(source='get_total_invested')
    total_returned = serializers.ReadOnlyField(source='get_total_returned')
    current_nav = serializers.ReadOnlyField(source='get_nav')
    calculated_xirr = serializers.ReadOnlyField(source='get_xirr')
    calculated_tvpi = serializers.ReadOnlyField(source='get_tvpi')
    calculated_dpi = serializers.ReadOnlyField(source='get_dpi')
    calculated_xnpv = serializers.ReadOnlyField(source='get_xnpv')
    gap_to_target_irr = serializers.ReadOnlyField(source='get_gap_to_target_irr')
    calculated_rvpi = serializers.SerializerMethodField()
    rvpi_color = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'target_irr', 'start_date', 'status', 'created_at',
            'total_invested', 'total_returned', 'current_nav',
            'calculated_xirr', 'calculated_tvpi', 'calculated_dpi',
            'calculated_xnpv', 'gap_to_target_irr', 'estimated_return',
            'calculated_rvpi',  # ДОБАВЛЕНО
            'rvpi_color',       # ДОБАВЛЕНО
        ]
    
    def get_calculated_rvpi(self, obj):
        """Получаем значение RVPI"""
        rvpi_data = obj.get_rvpi()
        return rvpi_data.get('value', 0)
    
    def get_rvpi_color(self, obj):
        """Получаем цвет для RVPI badge"""
        rvpi_data = obj.get_rvpi()
        color_map = {
            'green': 'success',
            'orange': 'warning', 
            'purple': 'purple'
        }
        return color_map.get(rvpi_data.get('color', 'gray'), 'secondary')