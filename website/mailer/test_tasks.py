from unittest.mock import call, MagicMock, patch

from django.test import override_settings, TestCase

from .tasks import _send_mails, send_mass_mails


class SendMassMailsTests(TestCase):
    @override_settings(MAILER_GROUP_BY=3)
    @patch("mailer.tasks._send_mails_bulk.delay")
    def test_should_split_mail_in_small_groups(self, mock_bulk):
        send_mass_mails([x for x in range(0, 11)])

        mock_bulk.assert_has_calls(
            [call([0, 1, 2]), call([3, 4, 5]), call([6, 7, 8]), call([9, 10])]
        )
        self.assertEqual(mock_bulk.call_count, 4)


class SendMailsTests(TestCase):
    @patch("mailer.tasks.get_connection")
    def test_should_send_mails(self, mock_get_connection):
        mock_connection = MagicMock()
        mock_connection.send_messages.return_value = 1
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        mock_task = MagicMock()

        _send_mails(mock_task, [1, 2, 3, 4])

        mock_task.retry.assert_not_called()
        self.assertEqual(mock_task.update_state.call_count, 4)
        mock_task.update_state.assert_has_calls(
            [
                call(state="PROGRESS", meta={"progress": 25.0}),
                call(state="PROGRESS", meta={"progress": 50.0}),
                call(state="PROGRESS", meta={"progress": 75.0}),
                call(state="PROGRESS", meta={"progress": 100}),
            ]
        )
        self.assertEqual(mock_connection.send_messages.call_count, 4)
        mock_connection.send_messages.assert_has_calls(
            [
                call([1]),
                call([2]),
                call([3]),
                call([4]),
            ]
        )

    @patch("mailer.tasks.get_connection")
    @override_settings(MAILER_DELAY_BEFORE_RETRY=4)
    def test_should_resend_mails_in_error(self, mock_get_connection):
        mock_connection = MagicMock()
        mock_connection.send_messages.side_effect = [1, 0, 0, 1]
        mock_get_connection.return_value.__enter__.return_value = mock_connection
        mock_task = MagicMock()
        mock_task.retry.return_value = Exception("RETRY")

        with self.assertRaisesRegex(Exception, "RETRY"):
            _send_mails(mock_task, [1, 2, 3, 4])

        self.assertEqual(mock_task.retry.call_count, 1)
        mock_task.retry.assert_has_calls([call(countdown=4, args=[[2, 3]], kwargs={})])
        self.assertEqual(mock_task.update_state.call_count, 4)
        mock_task.update_state.assert_has_calls(
            [
                call(state="PROGRESS", meta={"progress": 25.0}),
                call(state="PROGRESS", meta={"progress": 50.0}),
                call(state="PROGRESS", meta={"progress": 75.0}),
                call(state="PROGRESS", meta={"progress": 100}),
            ]
        )
        self.assertEqual(mock_connection.send_messages.call_count, 4)
        mock_connection.send_messages.assert_has_calls(
            [
                call([1]),
                call([2]),
                call([3]),
                call([4]),
            ]
        )
