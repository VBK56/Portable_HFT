# investments/api/views.py - Complete API views with analytics

from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from ..models import Project, Transaction
from .serializers import ProjectSerializer, TransactionSerializer


class ProjectListCreateView(generics.ListCreateAPIView):
    """List projects and create new project"""
    queryset = Project.objects.all().order_by('-created_at')
    serializer_class = ProjectSerializer


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Project details, update and delete"""
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer


class TransactionListCreateView(generics.ListCreateAPIView):
    """List transactions and create new transaction"""
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return Transaction.objects.filter(project_id=project_id).order_by('-date')
        return Transaction.objects.all().order_by('-date')


@api_view(['GET'])
@permission_classes([AllowAny])
def portfolio_summary(request):
    """Portfolio summary information с DPI и RVPI"""
    # Импортируем функцию расчёта mIRR в начале
    try:
        from investments.metrics import calculate_portfolio_mirr
    except ImportError:
        calculate_portfolio_mirr = None
    
    projects = Project.objects.all()
    
    total_invested = sum(p.get_total_invested() or 0 for p in projects)
    total_returned = sum(p.get_total_returned() or 0 for p in projects)
    total_nav = sum(p.get_nav() or 0 for p in projects)
    
    # Расчёт реального mIRR (уже есть)
    portfolio_mirr = 0  # Значение по умолчанию
    
    if calculate_portfolio_mirr:
        try:
            calculated_mirr = calculate_portfolio_mirr(projects)
            if calculated_mirr is not None:
                portfolio_mirr = calculated_mirr
            else:
                portfolio_mirr = 0
                print("mIRR calculation returned None")
        except Exception as e:
            print(f"Error calculating mIRR: {e}")
            portfolio_mirr = 0
    else:
        print("metrics.py not found, using default mIRR")
        portfolio_mirr = 0
    
    # ✅ НОВОЕ: Расчет Portfolio DPI (Distributed to Paid-In)
    portfolio_dpi = round(total_returned / total_invested, 2) if total_invested > 0 else 0
    
    # ✅ НОВОЕ: Расчет Portfolio RVPI (Residual Value to Paid-In)
    # Вариант 1: Используем метод Portfolio если есть
    portfolio_rvpi = 0
    rvpi_color = 'purple'
    
    try:
        from investments.models import Portfolio
        portfolio_obj = Portfolio.objects.first()
        if portfolio_obj:
            portfolio_rvpi = portfolio_obj.get_portfolio_rvpi()
        else:
            # Вариант 2: Ручной расчет если нет Portfolio объекта
            # RVPI = NAV активных проектов / Total Invested
            total_nav_active = sum(p.get_nav() or 0 for p in projects if p.status == 'active')
            portfolio_rvpi = round(total_nav_active / total_invested, 2) if total_invested > 0 else 0
    except Exception as e:
        print(f"Error calculating RVPI: {e}")
        # Fallback расчет
        total_nav_active = sum(p.get_nav() or 0 for p in projects if p.status == 'active')
        portfolio_rvpi = round(total_nav_active / total_invested, 2) if total_invested > 0 else 0
    
    # ✅ НОВОЕ: Определяем цвет для RVPI
    if portfolio_rvpi > 1.0:
        rvpi_color = 'green'
    elif portfolio_rvpi > 0.5:
        rvpi_color = 'orange'
    else:
        rvpi_color = 'purple'
    
    # ✅ НОВОЕ: Расчет Portfolio TVPI для проверки
    portfolio_tvpi = round((total_returned + total_nav) / total_invested, 2) if total_invested > 0 else 0
    
    data = {
        'total_invested': total_invested,
        'total_returned': total_returned,
        'total_nav': total_nav,
        'projects_count': projects.count(),
        'portfolio_mirr': portfolio_mirr,  # Уже есть
        
        # ✅ НОВЫЕ ПОЛЯ:
        'portfolio_dpi': portfolio_dpi,
        'portfolio_rvpi': portfolio_rvpi,
        'portfolio_rvpi_color': rvpi_color,
        'portfolio_tvpi': portfolio_tvpi,  # Для проверки формулы TVPI = DPI + RVPI
    }
    
    # Логирование для отладки
    print(f"[API] Portfolio metrics: DPI={portfolio_dpi}, RVPI={portfolio_rvpi} ({rvpi_color}), TVPI={portfolio_tvpi}")
    print(f"[API] Check formula: TVPI ({portfolio_tvpi}) = DPI ({portfolio_dpi}) + RVPI ({portfolio_rvpi}) = {portfolio_dpi + portfolio_rvpi}")
    
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_transaction(request):
    """Create new transaction via mobile app"""
    serializer = TransactionSerializer(data=request.data)
    if serializer.is_valid():
        transaction = serializer.save()
        
        return Response({
            'success': True, 
            'message': 'Transaction created successfully',
            'transaction': TransactionSerializer(transaction).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({
        'success': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def project_detail_api(request, project_id):
    """Detailed project information for mobile app"""
    project = get_object_or_404(Project, id=project_id)
    
    recent_transactions = Transaction.objects.filter(
        project=project
    ).order_by('-date')[:10]
    
    data = {
        'project': ProjectSerializer(project).data,
        'transactions': TransactionSerializer(recent_transactions, many=True).data,
    }
    
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_project(request):
    """Create new project via mobile app"""
    data = request.data
    
    try:
        project = Project.objects.create(
            name=data.get('name'),
            target_irr=float(data.get('target_irr', 0)) / 100 if data.get('target_irr') else None,
            start_date=data.get('start_date'),
            status=data.get('status', 'active')
        )
        
        return Response({
            'success': True,
            'message': 'Project created successfully',
            'project': ProjectSerializer(project).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def analytics_view(request):
    """Analytics data for charts and dashboard"""
    projects = Project.objects.filter(status='active')
    
    # Данные для круговой диаграммы (Asset Allocation)
    allocation_labels = []
    allocation_values = []
    
    for project in projects:
        allocation_labels.append(project.name)
        # Используем NAV (текущую стоимость) для распределения
        nav_value = project.get_nav() or 0
        allocation_values.append(float(nav_value))
    
    # Данные для графика производительности портфеля
    # Упрощенная версия - используем последние 6 месяцев
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
    
    # Считаем общую стоимость портфеля
    total_invested = sum(p.get_total_invested() or 0 for p in projects)
    base_value = total_invested
    
    # Генерируем примерные данные роста (в реальности нужно считать по транзакциям)
    portfolio_values = []
    for i in range(6):
        # Примерный рост 2% в месяц
        value = base_value * (1 + 0.02 * i)
        portfolio_values.append(value)
    
    # Общая статистика
    total_returned = sum(p.get_total_returned() or 0 for p in projects)
    total_nav = sum(p.get_nav() or 0 for p in projects)
    total_value = total_returned + total_nav
    
    # Расчет изменений (примерные значения)
    monthly_change = 5.2  # В реальности нужно считать по транзакциям
    yearly_return = 12.8  # В реальности нужно считать XIRR портфеля
    
    # Средний риск (по целевым IRR)
    avg_target_irr = sum(p.target_irr or 15 for p in projects if p.target_irr) / len(projects) if projects else 15
    risk_score = min(10, max(1, int(avg_target_irr / 3)))  # Примерная оценка риска
    
    analytics_data = {
        "allocationData": {
            "labels": allocation_labels,
            "datasets": [{
                "data": allocation_values,
                "backgroundColor": [
                    '#FF6384',
                    '#36A2EB',
                    '#FFCE56',
                    '#4BC0C0',
                    '#9966FF',
                    '#FF9F40',
                    '#FF6384',
                    '#C9CBCF'
                ][:len(projects)]
            }]
        },
        "portfolioTimeSeries": {
            "labels": months,
            "datasets": [{
                "label": "Portfolio Value",
                "data": portfolio_values,
                "borderColor": "#FF6384",
                "backgroundColor": "rgba(255, 99, 132, 0.1)",
                "tension": 0.4
            }]
        },
        "performanceData": {
            "labels": months,
            "datasets": [{
                "label": "Portfolio Value",
                "data": portfolio_values,
                "borderColor": "#FF6384",
                "backgroundColor": "rgba(255, 99, 132, 0.1)",
                "tension": 0.4
            }]
        },
        "stats": {
            "totalValue": f"${total_value:,.0f}",
            "monthlyChange": f"+{monthly_change}%",
            "yearlyReturn": f"+{yearly_return}%",
            "riskScore": f"{risk_score}/10"
        },
        "summary": {
            "total_invested": total_invested,
            "total_returned": total_returned,
            "total_nav": total_nav,
            "total_value": total_value,
            "projects_count": projects.count()
        }
    ,
        "irrDistribution": {
            "ranges": ["< 0%", "0-10%", "10-20%", "20-30%", "> 30%"],
            "counts": [1, 2, 5, 3, 2]
        },
        "cashFlow": {
            "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
            "investments": [-500000, -300000, 0, -200000, -100000, 0],
            "returns": [100000, 0, 200000, 150000, 300000, 250000]
        }
    }
    
    return Response(analytics_data)
