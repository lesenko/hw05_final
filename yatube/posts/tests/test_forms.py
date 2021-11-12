import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from posts.forms import PostForm, CommentForm
from posts.models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostCreateEditFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Test User')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_edit = Group.objects.create(
            title='Тест',
            slug='test-slug-edit',
            description='Тестовое описание',
        )
        cls.group_no_edit = Group.objects.create(
            title='Тест',
            slug='test-slug-no-edit',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.form = PostForm()

        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x01\x00'
            b'\x01\x00\x00\x00\x00\x21\xf9\x04'
            b'\x01\x0a\x00\x01\x00\x2c\x00\x00'
            b'\x00\x00\x01\x00\x01\x00\x00\x02'
            b'\x02\x4c\x01\x00\x3b'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': PostCreateEditFormTests.post.text,
            'group': PostCreateEditFormTests.group.pk,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        last_post = Post.objects.all().order_by('id').last()
        self.assertEqual(last_post.text, form_data['text'])
        self.assertEqual(last_post.group.pk, form_data['group'])
        path_to_img = f'{Post.image.field.upload_to}'+str(form_data['image'])
        self.assertEqual(last_post.image, path_to_img)

    def test_edit_post(self):
        """Валидная форма редактирует и сохраняет запись в Post."""
        posts_count = Post.objects.count()
        self.post.text = 'Новый текст'
        self.post.group.pk = PostCreateEditFormTests.group_edit.pk
        form_data = {
            'text': self.post.text,
            'group': PostCreateEditFormTests.group_edit.pk,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(self.post.text, form_data['text'])
        self.assertEqual(
            self.post.group.pk, form_data['group']
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})
        )

    def test_create_post_by_guest(self):
        """Гость не может создать пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': PostCreateEditFormTests.post.text,
            'group': PostCreateEditFormTests.group.pk,
        }
        response = self.client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/create/')
        self.assertEqual(Post.objects.count(), posts_count)

    def test_edit_post_by_guest(self):
        """Гость не может редактировать пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Еще один новый текст',
            'group': PostCreateEditFormTests.group_no_edit.pk,
        }
        response = self.client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.pk}),
            data=form_data,
            follow=True
        )
        self.assertNotEqual(self.post.text, form_data['text'])
        self.assertNotEqual(
            self.post.group.pk, form_data['group']
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.post.pk}/edit/'
        )
        self.assertEqual(Post.objects.count(), posts_count)


class CommentFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Test User')
        cls.author_post = User.objects.create_user(username='Test Author')
        cls.group = Group.objects.create(
            title='Заголовок',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.author_post,
            text='Тестовый текст',
            group=cls.group,
        )
        cls.form = CommentForm()
        cls.comment_author = User.objects.create_user(
            username='Comment Author'
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    def test_add_comment(self):
        """Валидная форма создает комментарий на странице поста."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment', kwargs={'post_id': self.post.pk}
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse(
            'posts:post_detail', kwargs={'post_id': self.post.pk})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        response = self.authorized_client.post(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.pk}
            )
        )
        comment = Comment.objects.filter(
            author = CommentFormTests.user,
            text = form_data['text']
        )
        self.assertTrue(comment[0] in response.context['comments'])

    def test_add_comment_by_guest_client(self):
        """Гость не может добавить комментарий."""
        comments_count = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.client.post(
            reverse(
                'posts:add_comment', kwargs={'post_id': self.post.pk}
            ),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response, f'/auth/login/?next=/posts/{self.group.id}/comment/'
        )
        self.assertEqual(Comment.objects.count(), comments_count)
