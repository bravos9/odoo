# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailComposeMessage(models.TransientModel):

    _inherit = 'mail.compose.message'

    automation_stats_ids = fields.Many2many('marketing.automation.statistics',  string='Mailing List')

    @api.multi
    def get_mail_values(self, res_ids):
        """ Override method to link mail automation activity with mail statistics"""
        res = super(MailComposeMessage, self).get_mail_values(res_ids)
        if self.composition_mode == 'mass_mail' and self.automation_stats_ids:
            stats_map = dict([(stat.workitem_id.res_id, stat) for stat in self.automation_stats_ids])
            for res_id in res_ids:
                mail_values = res[res_id]
                stat_vals = {
                    'model': self.model,
                    'res_id': res_id,
                    'mass_mailing_id': self.mass_mailing_id.id,
                    'automation_stat_id': stats_map[res_id].id
                }
                if stats_map[res_id].workitem_id.test_mode:
                    mail_values['recipient_ids'] = []
                    mail_values['email_to'] = stats_map[res_id].workitem_id.test_email

                # Replaced all values again because campaign can be run on non-mass mailing model
                mail_values.update({
                    'mailing_id': self.mass_mailing_id.id,
                    'statistics_ids': [(0, 0, stat_vals)],
                    'notification': self.mass_mailing_id.reply_to_mode == 'thread',
                    'auto_delete': not self.mass_mailing_id.keep_archives,
                })
        return res
