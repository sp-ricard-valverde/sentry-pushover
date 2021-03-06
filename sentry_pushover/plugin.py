#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Sentry-Pushover
=============

License
-------
Copyright 2012 Janez Troha

This file is part of Sentry-Pushover.

Sentry-Pushover is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Sentry-Pushover is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Sentry-Pushover.  If not, see <http://www.gnu.org/licenses/>.
'''
import logging

from django import forms
from sentry.http import safe_urlopen
from sentry.plugins.bases.notify import NotifyPlugin

import sentry_pushover

logger = logging.getLogger(__name__)


class PushoverSettingsForm(forms.Form):
    groupkey = forms.CharField(
        help_text='Your user key. See https://pushover.net/')
    apikey = forms.CharField(
        help_text='Application API token. See https://pushover.net/apps/')
    subscription = forms.CharField(
        help_text='The group subscription Url. You should visit this if you want to get Pushover notifications from '
                  'this project')
    priority = forms.ChoiceField(
        required=False,
        initial='0',
        choices=[
            ('-2', 'Lowest'),
            ('-1', 'Low'),
            ('0', 'Normal'),
            ('1', 'High'),
            ('2', 'Emergency'),
        ],
        help_text='High-priority notifications, also bypasses quiet hours.')
    level = forms.ChoiceField(
        required=False,
        initial=logging.ERROR,
        choices=[
            (logging.DEBUG, 'Debug'),
            (logging.INFO, 'Info'),
            (logging.WARNING, 'Warning'),
            (logging.ERROR, 'Error'),
            (logging.FATAL, 'Fatal'),
        ],
        help_text='The minimum level of the message to be sent to Pushover.')


class PushoverNotifications(NotifyPlugin):
    # author = 'Janez Troha'
    # author_url = 'http://dz0ny.info'
    author = 'Sentry Team'
    author_url = 'https://github.com/getsentry/sentry-pushover'

    title = 'Pushover'

    conf_title = 'Pushover'
    conf_key = 'pushover'
    slug = 'pushover'

    resource_links = [
        ('Bug Tracker', 'https://github.com/getsentry/sentry-pushover/issues'),
        ('Source', 'https://github.com/getsentry/sentry-pushover'),
    ]

    version = sentry_pushover.VERSION
    project_conf_form = PushoverSettingsForm

    def can_enable_for_projects(self):
        return True

    def is_configured(self, project):
        return all(
            self.get_option(key, project)
            for key in ('groupkey', 'subscription', 'apikey')
        )

    def notify(self, notification):
        event = notification.event
        group = event.group
        project = group.project

        title = '%s: %s' % (project.name, group.title)
        link = group.get_absolute_url()

        tags = event.get_tags()
        level = getattr(logging, event.get_tag('level').upper())

        if level >= int(self.get_option('level', project)):

            message = event.message + '\n'
            if tags:
                message = 'Tags: %s\n' % (', '.join(
                    '%s=%s' % (k, v) for (k, v) in tags))

            # see https://pushover.net/api
            # We can no longer send JSON because pushover disabled incoming
            # JSON data: http://updates.pushover.net/post/39822700181/
            data = {
                'user': self.get_option('groupkey', project),
                'token': self.get_option('apikey', project),
                'message': message,
                'title': title,
                'url': link,
                'url_title': 'Details',
                'priority': self.get_option('priority', project)
            }

            rv = safe_urlopen('https://api.pushover.net/1/messages.json',
                              data=data)
            if not rv.ok:
                logger.error(rv.text)
                raise RuntimeError('Failed to notify: %s' % rv)
        else:

            logger.info("Pushover notification skipped due to project notification level configuration")
