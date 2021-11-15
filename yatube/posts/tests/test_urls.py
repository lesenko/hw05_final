from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )

    def setUp(self):
        self.user = User.objects.create_user(username='MichaelLermontov')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_pages_exists_at_desired_location(self):
        """Страницы доступны любому пользователю."""
        page_names = {
            f'/group/{PostURLTests.group.slug}/',
            f'/profile/{self.user.username}/',
            f'/posts/{PostURLTests.post.pk}/',
        }
        for page_name in page_names:
            with self.subTest(page_name=page_name):
                response = self.authorized_client.get(page_name)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_exists_at_desired_location(self):
        """Страница post_create доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_exists_at_desired_location(self):
        """Страница post_edit доступна авторизованному пользователю."""
        if self.authorized_client == PostURLTests.post.author:
            response = self.authorized_client.get(
                f'/posts/{PostURLTests.post.pk}/edit/'
            )
            self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_unixisting_page_exists_at_desired_location(self):
        """Запрос к несуществующей странице вернёт ошибку 404."""
        response = self.client.get('/abcdefg/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_create_post_edit_pages_redirect_on_login(self):
        """Страницы create и post_edit перенаправят анонимного пользователя
        на страницу логина.
        """
        page_names = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{PostURLTests.post.pk}/edit/':
                f'/auth/login/?next=/posts/{PostURLTests.post.pk}/edit/',
        }
        for page_name, redirect_page in page_names.items():
            with self.subTest(page_name=page_name):
                response = self.client.get(page_name, follow=True)
                self.assertRedirects(response, (redirect_page))

    def test_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.user.username}/': 'posts/profile.html',
            f'/posts/{PostURLTests.post.pk}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_post_edit_page_uses_correct_template(self):
        if self.authorized_client == PostURLTests.post.author:
            response = self.authorized_client.get(
                f'/posts/{PostURLTests.post.pk}/'
            )
            self.assertTemplateUsed(response, 'posts/create_post.html')


class StaticURLTests(TestCase):
    def test_static_pages(self):
        static_pages = {
            '/',
            '/about/author/',
            '/about/tech/',
        }
        for static_page in static_pages:
            with self.subTest(static_page=static_page):
                response = self.client.get(static_page)
                self.assertEqual(response.status_code, HTTPStatus.OK)
