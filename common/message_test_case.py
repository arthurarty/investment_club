from django.contrib.messages.test import MessagesTestMixin
from django.test import TestCase


class MsgTestCase(MessagesTestMixin, TestCase):
    """
    Adds the MessagesTestMixin to the TestCase.
    Use this when you are testing views that make use of messages.
    """
