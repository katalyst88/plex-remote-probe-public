from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from boards.models import Category, Post, Thread
from boards.templatetags.forum_tags import render_markdown


class ForumTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.alice = User.objects.create_user("alice", password="pw-alice-123")
        cls.bob = User.objects.create_user("bob", password="pw-bob-123")
        cls.staff = User.objects.create_user("mod", password="pw-mod-123", is_staff=True)
        cls.general = Category.objects.create(name="General", slug="general")
        cls.news = Category.objects.create(name="News", slug="news", staff_only_posting=True)
        cls.lounge = Category.objects.create(name="Lounge", slug="lounge", members_only=True)

    def make_thread(self, author=None, category=None, title="A test thread", body="Hello there"):
        thread = Thread.objects.create(category=category or self.general, author=author or self.alice, title=title)
        Post.objects.create(thread=thread, author=author or self.alice, body=body)
        return thread


class BrowsingTests(ForumTestCase):
    def test_index_lists_categories(self):
        response = self.client.get(reverse("boards:index"))
        self.assertContains(response, "General")
        self.assertContains(response, "Lounge")

    def test_thread_page_renders_and_counts_views(self):
        thread = self.make_thread()
        response = self.client.get(thread.get_absolute_url())
        self.assertContains(response, "Hello there")
        thread.refresh_from_db()
        self.assertEqual(thread.view_count, 1)

    def test_wrong_slug_redirects_to_canonical(self):
        thread = self.make_thread()
        response = self.client.get(reverse("boards:thread_short", args=[thread.pk]))
        self.assertRedirects(response, thread.get_absolute_url(), status_code=301)

    def test_reserved_slug_is_suffixed(self):
        thread = self.make_thread(title="Reply")
        self.assertEqual(thread.slug, "reply-thread")
        self.assertEqual(self.client.get(thread.get_absolute_url()).status_code, 200)

    def test_pinned_threads_list_first(self):
        old = self.make_thread(title="Old pinned thread")
        Thread.objects.filter(pk=old.pk).update(is_pinned=True, last_activity_at=timezone.now() - timedelta(days=5))
        self.make_thread(title="Fresh thread here")
        threads = list(self.client.get(self.general.get_absolute_url()).context["page"])
        self.assertEqual(threads[0].title, "Old pinned thread")

    def test_search_matches_title_and_body(self):
        self.make_thread(title="Pricing vintage denim", body="nothing")
        self.make_thread(title="Unrelated topic", body="let's talk about denim")
        self.make_thread(title="Something else", body="nope")
        response = self.client.get(reverse("boards:search"), {"q": "denim"})
        titles = {t.title for t in response.context["page"]}
        self.assertEqual(titles, {"Pricing vintage denim", "Unrelated topic"})


class PostingTests(ForumTestCase):
    def test_anonymous_cannot_start_thread(self):
        url = reverse("boards:new_thread", args=["general"])
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={url}")

    def test_member_starts_thread_with_opening_post(self):
        self.client.force_login(self.alice)
        response = self.client.post(
            reverse("boards:new_thread", args=["general"]), {"title": "My first thread", "body": "Opening words"}
        )
        thread = Thread.objects.get(title="My first thread")
        self.assertRedirects(response, thread.get_absolute_url())
        self.assertEqual(thread.posts.get().body, "Opening words")

    def test_staff_only_category_blocks_members(self):
        self.client.force_login(self.alice)
        response = self.client.get(reverse("boards:new_thread", args=["news"]))
        self.assertEqual(response.status_code, 403)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(reverse("boards:new_thread", args=["news"])).status_code, 200)

    def test_reply_bumps_thread_and_lands_on_last_page(self):
        thread = self.make_thread()
        Thread.objects.filter(pk=thread.pk).update(last_activity_at=timezone.now() - timedelta(days=1))
        self.client.force_login(self.bob)
        with self.settings(FORUM_POSTS_PER_PAGE=1):
            response = self.client.post(reverse("boards:reply", args=[thread.pk]), {"body": "Nice one"})
        post = Post.objects.get(body="Nice one")
        self.assertRedirects(response, f"{thread.get_absolute_url()}?page=2#post-{post.pk}", fetch_redirect_response=False)
        thread.refresh_from_db()
        self.assertEqual(thread.last_activity_at, post.created_at)

    def test_locked_thread_rejects_member_replies_but_not_staff(self):
        thread = self.make_thread()
        thread.is_locked = True
        thread.save()
        self.client.force_login(self.bob)
        self.assertEqual(self.client.post(reverse("boards:reply", args=[thread.pk]), {"body": "hi"}).status_code, 403)
        self.client.force_login(self.staff)
        self.client.post(reverse("boards:reply", args=[thread.pk]), {"body": "Staff note"})
        self.assertTrue(thread.posts.filter(body="Staff note").exists())

    def test_only_author_or_staff_can_edit(self):
        thread = self.make_thread()
        post = thread.posts.get()
        url = reverse("boards:edit_post", args=[post.pk])
        self.client.force_login(self.bob)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.alice)
        self.client.post(url, {"title": "Renamed thread", "body": "Edited body"})
        post.refresh_from_db()
        thread.refresh_from_db()
        self.assertEqual(post.body, "Edited body")
        self.assertIsNotNone(post.edited_at)
        self.assertEqual(thread.title, "Renamed thread")
        self.assertEqual(thread.slug, "renamed-thread")

    def test_deleting_opening_post_deletes_thread(self):
        thread = self.make_thread()
        Post.objects.create(thread=thread, author=self.bob, body="reply")
        self.client.force_login(self.alice)
        self.client.post(reverse("boards:delete_post", args=[thread.posts.first().pk]))
        self.assertFalse(Thread.objects.filter(pk=thread.pk).exists())

    def test_deleting_reply_keeps_thread(self):
        thread = self.make_thread()
        reply = Post.objects.create(thread=thread, author=self.bob, body="reply")
        self.client.force_login(self.bob)
        self.client.post(reverse("boards:delete_post", args=[reply.pk]))
        self.assertTrue(Thread.objects.filter(pk=thread.pk).exists())
        self.assertEqual(thread.posts.count(), 1)

    def test_like_toggles_and_self_like_ignored(self):
        post = self.make_thread().posts.get()
        url = reverse("boards:like", args=[post.pk])
        self.client.force_login(self.bob)
        self.client.post(url)
        self.assertEqual(post.likes.count(), 1)
        self.client.post(url)
        self.assertEqual(post.likes.count(), 0)
        self.client.force_login(self.alice)
        self.client.post(url)
        self.assertEqual(post.likes.count(), 0)

    def test_moderation_is_staff_only(self):
        thread = self.make_thread()
        url = reverse("boards:moderate", args=[thread.pk, "pin"])
        self.client.force_login(self.alice)
        self.assertEqual(self.client.post(url).status_code, 403)
        self.client.force_login(self.staff)
        self.client.post(url)
        thread.refresh_from_db()
        self.assertTrue(thread.is_pinned)


class MembersOnlyTests(ForumTestCase):
    def test_free_user_sees_upsell(self):
        thread = self.make_thread(category=self.lounge, author=self.staff, title="Secret stuff")
        self.client.force_login(self.alice)
        response = self.client.get(thread.get_absolute_url())
        self.assertEqual(response.status_code, 403)
        self.assertNotContains(response, "Hello there", status_code=403)

    def test_members_only_threads_hidden_from_search(self):
        self.make_thread(category=self.lounge, author=self.staff, title="Secret denim tips")
        response = self.client.get(reverse("boards:search"), {"q": "denim"})
        self.assertEqual(list(response.context["page"]), [])

    def test_active_member_can_read(self):
        self.alice.membership_tier = User.Tier.MEMBER
        self.alice.membership_expires_at = timezone.now() + timedelta(days=30)
        self.alice.save()
        thread = self.make_thread(category=self.lounge, author=self.staff)
        self.client.force_login(self.alice)
        self.assertContains(self.client.get(thread.get_absolute_url()), "Hello there")

    def test_expired_membership_loses_access(self):
        self.alice.membership_tier = User.Tier.MEMBER
        self.alice.membership_expires_at = timezone.now() - timedelta(days=1)
        self.alice.save()
        self.assertFalse(self.alice.has_active_membership)


class MarkdownTests(TestCase):
    def test_script_tags_are_stripped(self):
        html = render_markdown("hi <script>alert(1)</script>")
        self.assertNotIn("<script", html)

    def test_javascript_links_are_neutralised(self):
        html = render_markdown("[x](javascript:alert(1))")
        self.assertNotIn("javascript:", html)

    def test_links_get_nofollow(self):
        html = render_markdown("see https://example.com")
        self.assertIn('rel="nofollow noopener ugc"', html)

    def test_formatting_survives(self):
        html = render_markdown("**bold** and `code`")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<code>code</code>", html)
