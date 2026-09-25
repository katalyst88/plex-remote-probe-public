from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User
from boards.models import Category, Post, Thread

CATEGORIES = [
    ("Announcements", "announcements", "News and updates from the team.", {"staff_only_posting": True}),
    ("Introductions", "introductions", "New here? Say hello, what you sell and where.", {}),
    ("Sourcing", "sourcing", "Op shops, garage sales, auctions, bulk lots: where and how you find stock.", {}),
    ("Pricing & valuation", "pricing", "What's it worth? Get a second opinion before you list.", {}),
    ("Listing & photos", "listing", "Titles, descriptions, photography and getting found in search.", {}),
    ("Platforms", "platforms", "eBay, Depop, Vinted, Marketplace, Poshmark and the rest: fees, rules, algorithms.", {}),
    ("Shipping & packaging", "shipping", "Postage costs, carriers, packaging and dealing with returns.", {}),
    ("Wins & sold", "wins", "Show off your best flips and what sold this week.", {}),
    ("Members' lounge", "lounge", "Deeper dives, sell-through data and strategy for paying members.", {"members_only": True}),
]


class Command(BaseCommand):
    help = "Create starter categories, and with --demo some sample users and threads."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Also create demo users and threads.")

    @transaction.atomic
    def handle(self, *args, demo=False, **options):
        for position, (name, slug, description, flags) in enumerate(CATEGORIES):
            Category.objects.update_or_create(
                slug=slug, defaults={"name": name, "description": description, "position": position, **flags}
            )
        self.stdout.write(self.style.SUCCESS(f"{len(CATEGORIES)} categories ready."))
        if not demo:
            return

        def user(username, **extra):
            obj, created = User.objects.get_or_create(username=username, defaults=extra)
            if created:
                obj.set_password("demo-password-123")
                obj.save()
            return obj

        admin = user("admin", display_name="The Team", is_staff=True, is_superuser=True, email="admin@example.com")
        mia = user("mia", display_name="Mia Tran", location="Brisbane", bio="Thrifter, reseller, spreadsheet enjoyer.")
        sam = user("sam", display_name="Sam K", location="Melbourne")

        def thread(category_slug, author, title, body, replies=(), **flags):
            category = Category.objects.get(slug=category_slug)
            if Thread.objects.filter(category=category, title=title).exists():
                return
            t = Thread.objects.create(category=category, author=author, title=title, **flags)
            Post.objects.create(thread=t, author=author, body=body)
            for who, text in replies:
                Post.objects.create(thread=t, author=who, body=text)

        thread(
            "announcements", admin, "Welcome to the forum!",
            "This is the very first thread. **Read the guidelines**, be kind, and share what you know.\n\n"
            "- Search before you post\n- Use a clear title\n- Credit your sources",
            is_pinned=True,
        )
        thread(
            "introductions", mia, "Hi from Brisbane 👋",
            "Been reselling vintage for about two years, mostly on Depop and eBay. Keen to swap tips on pricing!",
            replies=[(sam, "Welcome Mia! What's your best-selling category?"),
                     (mia, "Denim, by a mile. Anything pre-2000 flies.")],
        )
        thread(
            "pricing", sam, "How do you work out a listing price?",
            "I keep underpricing things. Do you use a formula or just look at sold listings?",
            replies=[(mia, "> Do you use a formula\n\nSold listings from the last 90 days, then knock 10% off for a quick sale.")],
        )
        thread(
            "wins", mia, "Op shop Levi's 501 → $95",
            "Paid $8 on Saturday, sold Tuesday. Made in USA tag was the giveaway, always check the inside label!",
            replies=[(sam, "Nice flip! Which platform?"), (mia, "Depop. Took about 20 minutes to list.")],
        )
        self.stdout.write(self.style.SUCCESS("Demo users (password: demo-password-123) and threads created."))
