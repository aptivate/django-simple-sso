# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.deconstruct import deconstructible

from ..utils import gen_secret_key


@deconstructible
class SecretKeyGenerator(object):
    """
    Helper to give default values to Client.secret and Client.key
    """

    def __init__(self, field):
        self.field = field

    def __call__(self):
        key = gen_secret_key(64)

        if not db_table_exists(self.get_model()._meta.db_table):
            return key

        while self.get_model().objects.filter(**{self.field: key}).exists():
            key = gen_secret_key(64)
        return key


class ConsumerSecretKeyGenerator(SecretKeyGenerator):
    def get_model(self):
        return Consumer


class TokenSecretKeyGenerator(SecretKeyGenerator):
    def get_model(self):
        return Token


class Consumer(models.Model):
    name = models.CharField(max_length=255, unique=True)
    private_key = models.CharField(
        max_length=64, unique=True,
        default=ConsumerSecretKeyGenerator('private_key')
    )
    public_key = models.CharField(
        max_length=64, unique=True,
        default=ConsumerSecretKeyGenerator('public_key')
    )

    def __unicode__(self):
        return self.name

    def rotate_keys(self):
        self.secret = ConsumerSecretKeyGenerator('private_key')()
        self.key = ConsumerSecretKeyGenerator('public_key')()
        self.save()


class Token(models.Model):
    consumer = models.ForeignKey(Consumer, related_name='tokens')
    request_token = models.CharField(
        unique=True, max_length=64,
        default=TokenSecretKeyGenerator('request_token')
    )
    access_token = models.CharField(
        unique=True, max_length=64,
        default=TokenSecretKeyGenerator('access_token')
    )
    timestamp = models.DateTimeField(default=timezone.now)
    redirect_to = models.CharField(max_length=255)
    user = models.ForeignKey(
        getattr(settings, 'AUTH_USER_MODEL', 'auth.User'),
        null=True
    )

    def refresh(self):
        self.timestamp = timezone.now()
        self.save()


# https://gist.github.com/rctay/527113
def db_table_exists(table, cursor=None):
    try:
        if not cursor:
            from django.db import connection
            cursor = connection.cursor()
        if not cursor:
            raise Exception
        table_names = connection.introspection.get_table_list(cursor)
    except:
        raise Exception("Unable to determine if the table '%s' exists" % table)
    else:
        return table in table_names
