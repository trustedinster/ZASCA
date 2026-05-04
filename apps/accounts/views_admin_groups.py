from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import Group

from apps.accounts.provider_decorators import superadmin_required
from apps.accounts.models import GroupProfile


@superadmin_required
def group_list(request):
    group_profiles = GroupProfile.objects.select_related('group').order_by(
        'sort_order', 'group__name'
    )
    unprofiled_groups = Group.objects.filter(profile__isnull=True).order_by(
        'name'
    )

    context = {
        'group_profiles': group_profiles,
        'unprofiled_groups': unprofiled_groups,
        'active_nav': 'groups',
    }
    return render(request, 'admin_base/groups/group_list.html', context)


@superadmin_required
def group_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        auto_staff = request.POST.get('auto_staff') == 'on'

        if not name:
            messages.error(request, '用户组名称不能为空')
            return redirect('admin:admin_groups:group_create')

        if Group.objects.filter(name=name).exists():
            messages.error(request, f'用户组「{name}」已存在')
            return redirect('admin:admin_groups:group_create')

        group = Group.objects.create(name=name)
        GroupProfile.objects.create(
            group=group,
            is_default=False,
            description=description,
            auto_staff=auto_staff,
            sort_order=int(sort_order),
        )
        messages.success(request, f'用户组「{name}」创建成功')
        return redirect('admin:admin_groups:group_list')

    context = {
        'is_create': True,
        'active_nav': 'groups',
    }
    return render(request, 'admin_base/groups/group_form.html', context)


@superadmin_required
def group_update(request, pk):
    group_profile = get_object_or_404(GroupProfile, pk=pk)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        sort_order = request.POST.get('sort_order', 0)
        auto_staff = request.POST.get('auto_staff') == 'on'

        if not name:
            messages.error(request, '用户组名称不能为空')
            return redirect(
                'admin:admin_groups:group_edit', pk=group_profile.pk
            )

        if (
            Group.objects.filter(name=name)
            .exclude(pk=group_profile.group.pk)
            .exists()
        ):
            messages.error(request, f'用户组「{name}」已存在')
            return redirect(
                'admin:admin_groups:group_edit', pk=group_profile.pk
            )

        group_profile.group.name = name
        group_profile.group.save()
        group_profile.description = description
        group_profile.sort_order = int(sort_order)
        group_profile.auto_staff = auto_staff
        group_profile.save()

        for user in group_profile.group.user_set.all():
            user.sync_staff_status()

        messages.success(request, f'用户组「{name}」更新成功')
        return redirect('admin:admin_groups:group_list')

    context = {
        'group_profile': group_profile,
        'is_create': False,
        'active_nav': 'groups',
    }
    return render(request, 'admin_base/groups/group_form.html', context)


@superadmin_required
def group_delete(request, pk):
    group_profile = get_object_or_404(GroupProfile, pk=pk)

    if group_profile.is_default:
        messages.error(request, '默认用户组不可删除')
        return redirect('admin:admin_groups:group_list')

    if request.method == 'POST':
        group_name = group_profile.group.name
        group_profile.group.delete()
        messages.success(request, f'用户组「{group_name}」已删除')
        return redirect('admin:admin_groups:group_list')

    context = {
        'group_profile': group_profile,
        'active_nav': 'groups',
    }
    return render(
        request, 'admin_base/groups/group_confirm_delete.html', context
    )
