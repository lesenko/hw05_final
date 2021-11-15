from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post, Follow

User = get_user_model()


def function_for_check_context(self, post):
    self.assertEqual(post.text, self.post.text)
    self.assertEqual(post.author, self.post.author)
    self.assertEqual(post.group, self.group)
    self.assertEqual(post.id, self.post.pk)
    self.assertEqual(post.image, self.post.image)


class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.user = User.objects.create_user(username='Test Author')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': PostPagesTests.group.slug}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': self.user}
            ): 'posts/profile.html',
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            ): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }

        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_post_edit_uses_correct_template(self):
        if self.authorized_client == PostPagesTests.post.author:
            response = self.authorized_client.get(
                reverse(
                    'posts:post_edit',
                    kwargs={'username': self.user, 'post_id': self.post.pk}
                )
            )
            self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        function_for_check_context(self, first_object)

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_list', kwargs={'slug': PostPagesTests.group.slug}
            )
        )
        first_object = response.context['page_obj'][0]
        function_for_check_context(self, first_object)

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(response.context.get('author'), self.user)

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            )
        )
        self.assertEqual(
            response.context['author_post'].text, PostPagesTests.post.text
        )
        self.assertEqual(
            response.context['author_post'].group, self.group
        )
        self.assertEqual(
            response.context['author_post'].author, PostPagesTests.post.author
        )
        self.assertEqual(
            response.context['author_post'].image, PostPagesTests.post.image
        )

    def test_create_post_edit_show_correct_context(self):
        """Шаблон create_post_edit сформирован с правильным контекстом."""
        if self.authorized_client == PostPagesTests.post.author:
            response = self.authorized_client.get(
                reverse(
                    'posts:post_create', kwargs={'post_id': self.post.pk}
                )
            )
            form_fields = {
                'text': forms.fields.CharField,
                'group': forms.fields.ChoiceField,
                'is_edit': True,
            }
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context['form'].fields[value]
                    self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts_list = []
        for i in range(13):
            cls.posts_list.append(Post.objects.create(
                author=cls.user,
                text='TestText',
                group=cls.group,
            ))

    def test_first_page_index_contains_ten_records(self):
        """Kоличество постов на первой странице равно 10."""
        page_names = {
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        }
        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name)
                self.assertEqual(
                    len(response.context['page_obj']), settings.PAGINATOR_NUM
                )

    def test_second_page_index_contains_three_records(self):
        """Kоличество постов на второй странице равно 3."""
        page_names = {
            reverse('posts:index'),
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            ),
            reverse('posts:profile', kwargs={'username': self.user.username}),
        }
        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name + '?page=2')
                rest_posts = len(self.posts_list) - settings.PAGINATOR_NUM
                if rest_posts <= settings.PAGINATOR_NUM:
                    self.assertEqual(
                        len(response.context['page_obj']), rest_posts
                    )
                else:
                    self.assertEqual(
                        len(
                            response.context['page_obj']
                        ), settings.PAGINATOR_NUM
                    )


class CachTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Test User')
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
        )

    def test_cache_index_page(self):
        """Проверка кеширования главной страницы."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(CachTest.post, response.context['page_obj'][-1])
        new_post = Post.objects.create(
            author=self.user,
            text='Новый тестовый пост',
        )
        self.assertEqual(CachTest.post, response.context['page_obj'][-1])
        cache.clear()
        self.assertNotEqual(new_post, response.context['page_obj'][-1])


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='Test Author')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.user = User.objects.create_user(username='Test User')
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_new_post_on_follow_page_for_followers(self):
        """Новая запись автора появляется в ленте тех,
        кто на него подписан."""
        Follow.objects.create(user=self.user, author=self.author)
        new_post = Post.objects.create(
            author=self.post.author,
            text=self.post.text
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertTrue(new_post in response.context['page_obj'])

    def test_no_new_post_on_follow_page_for_users(self):
        """Новая запись автора не появляется в ленте тех,
        кто на него не подписан."""
        new_post = Post.objects.create(
            author=self.post.author,
            text=self.post.text
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertTrue(new_post not in response.context['page_obj'])

    def test_follow_by_authorized_client(self):
        """Авторизованный пользователь может подписываться
        на других пользователей."""
        response = self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        self.assertTrue(
            Follow.objects.filter(user=self.user, author=self.author).exists()
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.author})
        )

    def test_unfollow_by_authorized_client(self):
        """Авторизованный пользователь может отписываться от
        других пользователей."""
        response = self.authorized_client.get(
            reverse('posts:profile_follow', kwargs={'username': self.author})
        )
        response = self.authorized_client.get(
            reverse(
                'posts:profile_unfollow', kwargs={'username': self.author}
            )
        )
        self.assertFalse(
            Follow.objects.filter(user=self.user, author=self.author).exists()
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.author})
        )
