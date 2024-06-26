from datetime import date
from django.db.models import Q, F
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView, DetailView
from django.core.cache import cache

from blog.models import Tag, Post, Category
from config.models import SideBar
from comment.forms import CommentForm
from comment.models import Comment

"""
# 函数视图如下：
def post_list(request, category_id=None, tag_id=None):
    # 文章列表视图
    category = None
    tag = None
    if tag_id:
        post_list, tag = Post.get_by_tag(tag_id)
    elif category_id:
        post_list, category = Post.get_by_category(category_id)
    else:
        post_list = Post.latest_posts()
    context = {
        'tag': tag,
        'category': category,
        'post_list': post_list,
        'sidebars': SideBar.get_all(),
    }
    context.update(Category.get_navs())
    return render(request, 'blog/list.html', context)


def post_detail(request, post_id):
    # 文章详情页
    post = Post.get_post_detail(post_id)
    context = {
        'post': post,
        'sidebars': SideBar.get_all(),
    }
    context.update(Category.get_navs())
    return render(request, "blog/detail.html", context)
"""


class CommonViewMixin:
    """通用类：评论，上下导航栏"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'sidebars': SideBar.get_all(),
        })
        context.update(Category.get_navs())
        return context


# 类视图如下
class IndexView(CommonViewMixin, ListView):
    """首页类视图"""
    queryset = Post.latest_posts()
    paginate_by = 5  # 一页展示五条数据
    context_object_name = "post_list"  # 修改在模板中的对象名
    template_name = 'blog/list.html'


class CategoryView(IndexView):
    """分类页面视图，继承自首页"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        category_id = self.kwargs.get('category_id')  # 在url请求链接中找到category_id参数
        category = get_object_or_404(Category, pk=category_id)
        context.update({
            'category': category,
        })
        return context

    def get_queryset(self):
        """重写页面获取到的数据集, 根据分类过滤"""
        queryset = super().get_queryset()
        category_id = self.kwargs.get('category_id')  # self.kwargs指的是url的请求链接中带来的东西
        return queryset.filter(category_id=category_id)


class TagView(IndexView):
    """标签页，继承于首页类视图"""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tag_id = self.kwargs.get('tag_id')
        tag = get_object_or_404(Tag, pk=tag_id)
        context.update({
            'tag': tag,
        })
        return context

    def get_queryset(self):
        """重写数据集，根据标签进行筛选"""
        queryset = super().get_queryset()
        tag_id = self.kwargs.get('tag_id')
        return queryset.filter(tag_id=tag_id)


class PostDetailView(CommonViewMixin, DetailView):
    """文章详情页，继承通用类和DetailView类"""
    queryset = Post.latest_posts()
    template_name = 'blog/detail.html'
    context_object_name = "post"
    pk_url_kwarg = 'post_id'

    def get(self, request, *args, **kwargs):
        """处理get请求"""
        response = super().get(request, *args, **kwargs)
        self.handle_visited()
        return response

    def handle_visited(self):
        increase_pv = False
        increase_uv = False
        uid = self.request.uid
        pv_key = 'pv:%s:%s' % (uid, self.request.path)
        uv_key = 'uv:%s:%s:%s' % (uid, str(date.today()), self.request.path)
        if not cache.get(pv_key):
            increase_pv = True
            cache.set(pv_key, 1, 1 * 60)  # 1分钟有效

        if not cache.get(uv_key):
            increase_uv = True
            cache.set(uv_key, 1, 24 * 60 * 60)  # 24小时有效

        if increase_pv and increase_uv:
            Post.objects.filter(pk=self.object.id).update(pv=F('pv') + 1,
                                                          uv=F('uv') + 1)
        elif increase_pv:
            Post.objects.filter(pk=self.object.id).update(pv=F('pv') + 1)

        elif increase_uv:
            Post.objects.filter(pk=self.object.id).update(uv=F('uv') + 1)


class SearchView(IndexView):
    """搜索视图，继承自index视图"""

    # 将关键字获取到，并且添加到模板上下文中，用于关键词的展示
    def get_context_data(self, **kwargs):
        """增加关键字上下文"""
        context = super().get_context_data(**kwargs)
        context.update({
            'keyword': self.request.GET.get('keyword', ""),
        })
        return context

    def get_queryset(self):
        """重写展示的数据集"""
        queryset = super().get_queryset()
        keyword = self.request.GET.get('keyword')
        if not keyword:
            return queryset
        return queryset.filter(Q(title__icontains=keyword) | Q(desc__icontains=keyword))


class AuthorView(IndexView):
    """作者页面，也是继承自首页视图"""

    def get_queryset(self):
        queryset = super().get_queryset()
        author_id = self.kwargs.get('owner_id')
        return queryset.filter(owner_id=author_id)
