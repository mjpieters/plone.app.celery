Introduction
============

This package integrates the `Celery`_ distributed task queue into Plone. It
allows you to configure Celery from your zope.conf configuration file, and
make sending task messages honor the Zope transaction manager.

Configuration
=============

You can provide Celery configuration via the Zope configuration file. Here
is an example::

    %import plone.app.celery
    <celery-config celery>
        server-email no-reply@vandelay.com
        admins George Costanza, george@vandelay.com
        admins Cosmo Kramer, kosmo@vandelay.com
        
        <broker>
            host localhost
            port 5672
            user guest
            password guest
            vhost /
        </broker>
        
        <celery>
            ignore-result true
            disable-rate-limits true
            
            task-publish-retry true
            <task-publish-retry-policy>
               max-retries 5
               interval-start 0
               interval-step 1
               interval-max 0.5
            </task-publish-retry-policy>
            
            default-queue default
            <queues>
                default dict(binding_key='default', exchange='default')
                feeds   dict(binding_key='feeds', exchange='feeds')
            </queues>
            <routes>
                feed.tasks.import_feed dict(queue='feeds')
                images.compress        image.compression.Compress
            </routes>
        </celery>
    </celery-config>

You must use the `%import plone.app.celery` statement to import the Celery
configuration schema. The top-level section always is called `<celery-config>`
and that section must have a name (due to zope.conf limitations), but it's
name is otherwise ignored.

The Celery configuration is subdivided into namespaced sub-sections. Each
Celery configuration key (as defined in the `Celery configuration
documentation`_) consists of a namespace (such as `CELERY`, `CELERYD` or 
`BROKER`) and a configuration option (such as `HOST` or `ROUTES`); the only
exceptions are the `SERVER_EMAIL` and `ADMINS` options. See the `Celery
configuration defaults module`_ for a complete listing.

Note that many Celery options make no sense in a Zope server context as you
would normally only send task messages, not run a worker to process tasks.

Using this subdivision, the ZConfig schema for Celery puts these options into
a section for each namespace. Thus, all `BROKER` configuration is contained in
a `<broker>` section, with each broker option lower-cased, underscores
replaced with dashes. An option like `CELERY_TASK_PUBLISH_RETRY` thus becomes
`task_publish_retry` in the `<celery>` section.

The ZConfig schema enforces the type information set by Celery, and any option
that takes a tuple (such as `CELERY_TASK_ERROR_WHITELIST` or `ADMINS`) can
be listed multiple times in zope.conf to list all items.

Options that take a dictionary (such as `CELERY_RESULT_ENGINE_OPTIONS` or 
`CELERY_QUEUES`) are configured in zope.conf using a new section with the
option name, so in the case of `CELERY_QUEUES` add a `<queues>` section to
the `celery` section listing each queue on a new line. Values are interpreted
as python expressions.

Some options are handled specially:

* The `ADMINS` option takes a `name, email address` pair.
 
* `CELERY_TASK_RESULT_EXPIRES` is listed as a time delta using ZConfig
  formatting. The set of suffixes recognized by ZConfig are: ‘w’ (weeks), ‘d’
  (days), ‘h’ (hours), ‘m’ (minutes), ‘s’ (seconds). Values may be floats,
  for example:4w 2.5d 7h 12m 0.001s.

* For the `CELERY_ROUTES` option, you can either specify python classes named
  by a dotted path or a python dictionary.

By using the `%import plone.app.celery` line in your zope.conf configuration
file, you automatically configure Celery to use the plone.app.celery loader.
If you want to use a different loader, you need to set the `CELERY_LOADER`
environment variable before the configuration file is processed.

Credits
=======

Design and implementation: `Martijn Pieters`_, `Jarn AS`_

.. _`Celery`: http://celeryproject.org/
.. _`Celery configuration documentation`: http://ask.github.com/celery/configuration.html
.. _`Celery configuration defaults module`: https://github.com/ask/celery/blob/master/celery/app/defaults.py
.. _`Martijn Pieters`: mailto:mj@jarn.com
.. _`Jarn AS`: http://jarn.com
