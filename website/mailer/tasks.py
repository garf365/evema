import logging
import math

from django.conf import settings
from django.core.mail import get_connection

from celery import shared_task

logger = logging.getLogger(__name__)


def _send_mails(self, messages):
    logger.info(
        f"Try sending {len(messages)} - Try {self.request.retries}/{self.max_retries}"
    )
    not_sent = []
    quantile = math.floor(len(messages) / 100)
    done = 0
    try:
        with get_connection() as connection:
            logger.info(f"Try sending {messages}")
            while messages:
                msg = messages[0]

                logger.info(f"Try sending {msg}")
                res = connection.send_messages([msg])

                if res == 0:
                    logger.error(f"Error sending {msg}")
                    not_sent.append(msg)

                messages.pop(0)
                done += quantile
                self.update_state(state="PROGRESS", meta={"progress": done})
    except Exception as e:
        logger.error(f"Exception {e}")
        raise e

    not_sent += messages

    logger.info(f"Not sent: {len(not_sent)}")

    if not_sent:
        logger.debug(f"Retry for: {not_sent}")
        raise self.retry(
            countdown=getattr(settings, "MAILER_DELAY_BEFORE_RETRY", 30 * 60),
            args=[not_sent],
            kwargs={},
        )

    return not_sent


@shared_task(
    bind=True,
    rate_limit=getattr(settings, "MAILER_RATE_LIMIT", "12/h"),
    max_retries=getattr(settings, "MAILER_MAX_RETRY", 5),
)
def _send_mails_bulk(self, messages):
    _send_mails(self, messages)


@shared_task(
    bind=True,
    rate_limit=getattr(settings, "MAILER_RATE_LIMIT", "10/m"),
    max_retries=getattr(settings, "MAILER_MAX_RETRY", 5),
)
def send_mails(self, messages):
    _send_mails(self, messages)


@shared_task(bind=True, ignore_result=True)
def send_mass_mails(self, messages):
    GROUP_BY = getattr(settings, "MAILER_GROUP_BY", 10)
    logger.info(f"send mail by group of {GROUP_BY}")

    for idx in range(0, len(messages), GROUP_BY):
        _send_mails_bulk.delay(messages[idx : idx + GROUP_BY])  # noqa: E203
