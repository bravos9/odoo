# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailMailStats(models.Model):
    _inherit = 'mail.mail.statistics'

    # Added m2o field related to statistics so we can manage multiple instance of same record simultaneously (mainly used test mode)
    automation_stat_id = fields.Many2one('marketing.automation.statistics', string='Marketing Automation Activity', ondelete='cascade')

    # Inherited these methods to manage activity based on email response
    def set_opened(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = super(MailMailStats, self).set_opened(mail_mail_ids=mail_mail_ids, mail_message_ids=mail_message_ids)
        if statistics.automation_stat_id:
            statistics.automation_stat_id.process_mail_response('mail_open')
        return statistics

    def set_replied(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = super(MailMailStats, self).set_replied(mail_mail_ids=mail_mail_ids, mail_message_ids=mail_message_ids)
        if statistics.automation_stat_id:
            statistics.automation_stat_id.process_mail_response('mail_reply')
        return statistics

    def set_bounced(self, mail_mail_ids=None, mail_message_ids=None):
        statistics = super(MailMailStats, self).set_bounced(mail_mail_ids=mail_mail_ids, mail_message_ids=mail_message_ids)
        if statistics.automation_stat_id:
            statistics.automation_stat_id.process_mail_response('mail_bounce')
        return statistics

    def link_clicked(self):
        self.ensure_one()
        if self.automation_stat_id:
            self.automation_stat_id.process_mail_response('mail_click')
