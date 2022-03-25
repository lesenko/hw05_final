# Yatube

Yatube - социальная сеть для публикации дневников.

1. В проект добавлены кастомные страницы ошибок:
* 404 page_not_found
* 403 permission_denied_view

Написан тест, проверяющий, что страница 404 отдает кастомный шаблон.

2. С помощью sorl-thumbnail выведены иллюстрации к постам:
* в шаблон главной страницы,
* в шаблон профайла автора,
* в шаблон страницы группы,
* на отдельную страницу поста.

Написаны тесты, которые проверяют:
* при выводе поста с картинкой изображение передаётся в словаре context:
  * на главную страницу,
  * на страницу профайла,
  * на страницу группы,
  * на отдельную страницу поста;
* при отправке поста с картинкой через форму PostForm создаётся запись в базе данных.

3. Создана система комментариев.

Написана система комментирования записей. На странице поста под текстом записи выводится форма для отправки комментария, а ниже — список комментариев. Комментировать могут только авторизованные пользователи. Работоспособность модуля протестирована.

4. Кеширование главной страницы.

Список постов на главной странице сайта хранится в кэше и обновляется раз в 20 секунд.

5. Тестирование кэша.

Написан тест для проверки кеширования главной страницы. Логика теста: при удалении записи из базы, она остаётся в response.content главной страницы до тех пор, пока кэш не будет очищен принудительно.

6. Добавлена система подписки на авторов и создана лента их постов.
