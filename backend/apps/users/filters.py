from django.db.models import Q


def filter_users(queryset, params):
    q = params.get('q')
    if q:
        queryset = queryset.filter(
            Q(username__icontains=q) | Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q)
        )
    status = params.get('status')
    if status:
        queryset = queryset.filter(status=status)
    role = params.get('role')
    if role:
        queryset = queryset.filter(groups__name=role)
    return queryset.distinct()
