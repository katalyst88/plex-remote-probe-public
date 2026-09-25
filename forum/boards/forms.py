from django import forms

from .models import Post, Thread

BODY_HELP = "Markdown supported: **bold**, _italic_, `code`, lists, links and > quotes."


class ThreadForm(forms.ModelForm):
    body = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "placeholder": "What's on your mind?"}),
        max_length=20000,
        help_text=BODY_HELP,
    )

    class Meta:
        model = Thread
        fields = ("title",)
        widgets = {"title": forms.TextInput(attrs={"placeholder": "A clear, specific title"})}

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if len(title) < 5:
            raise forms.ValidationError("Titles need at least 5 characters.")
        return title


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ("body",)
        widgets = {"body": forms.Textarea(attrs={"rows": 6, "placeholder": "Write a reply…"})}
        help_texts = {"body": BODY_HELP}
        labels = {"body": "Your reply"}

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("Replies can't be empty.")
        return body
