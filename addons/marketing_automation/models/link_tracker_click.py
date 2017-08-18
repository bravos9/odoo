# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class LinkTrackerClick(models.Model):

    _inherit = 'link.tracker.click'

    @api.model
    def add_click(self, code, ip, country_code, stat_id=False):
        if stat_id:
            mail_stat = self.env['mail.mail.statistics'].sudo().browse(stat_id)
            if mail_stat.exists():
                mail_stat.link_clicked()
        return super(LinkTrackerClick, self).add_click(code, ip, country_code, stat_id=stat_id)
