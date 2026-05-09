class ProviderContextMixin:
    """
    提供商视图上下文混入类

    为提供商视图注入通用上下文变量（active_nav 等）。
    提供商和超管共用同一套模板和 URL，侧边栏通过
    {% if user.is_superuser %} 条件渲染实现差异化。
    """

    provider_page_title = '2c2a 提供商后台'

    def get_provider_context(self):
        return {
            'page_title': self.provider_page_title,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_provider_context())
        return context
