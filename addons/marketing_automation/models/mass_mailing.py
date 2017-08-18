# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class MassMailing(models.Model):

    _inherit = 'mail.mass_mailing'

    is_automation = fields.Boolean(default=False)
    automation_model_name = fields.Char()

    @api.depends('mailing_model')
    def _compute_model(self):
        """Override _compute_model becasue marketing automation can send mass mail in all model
           so computed mailing_model_real based on automation_model_name
        """
        automation_mass_mailing = self.filtered(lambda m: m.is_automation)
        for mass_mail in automation_mass_mailing:
            mass_mail.mailing_model_real = mass_mail.automation_model_name

        default_mass_mailing = self.filtered(lambda m: not m.is_automation)
        if default_mass_mailing:
            super(MassMailing, default_mass_mailing)._compute_model()

    def send_mail_automation(self, activity, wi_stats):
        """Send massmail, add proper utm values and set automation_stats in composer
            :param activity: marketing.activity recordset
            :param workitems_stats: marketing.automation.statistics recordset
        """
        self.ensure_one()
        # get res_ids from stat ids
        res_ids = wi_stats.mapped('workitem_id.res_id')
        composer_values = self.with_context(utm_campaign_id=activity.campaign_id.utm_campaign_id.id, utm_source_id=activity.utm_source_id.id).get_composer_values()
        composer_values['automation_stats_ids'] = [(6, 0, wi_stats.ids)]
        # add related stats ids for composer
        composer = self.env['mail.compose.message'].with_context(active_ids=res_ids).create(composer_values)
        composer.send_mail(auto_commit=True)

    def convert_links(self):
        """Override convert_links so we can add marketing automation campaign instead of mass mail campaign"""
        res = {}
        if len(self) == 1 and self.is_automation:
            html = self.body_html if self.body_html else ''
            vals = {'mass_mailing_id': self.id}
            utm_campaign_id = self.env.context.get('utm_campaign_id')
            utm_source_id = self.env.context.get('utm_source_id')
            if utm_campaign_id:
                vals['campaign_id'] = utm_campaign_id
            if utm_source_id:
                vals['source_id'] = utm_source_id
            if self.medium_id:
                vals['medium_id'] = self.medium_id.id
            res[self.id] = self.env['link.tracker'].convert_links(html, vals, blacklist=['/unsubscribe_from_list'])
        else:
            res = super(MassMailing, self).convert_links()
        return res
