# -*- coding: utf-8 -*-

from odoo import fields, models, api
from datetime import date
from datetime import datetime


class ProductConfiguration(models.Model):
    _inherit = "product.attribute"

    def _get_default_uom_id(self):
        return self.env["product.uom"].search([], limit=1, order='id').id

    type = fields.Selection(selection_add=[('custom_value','Custom Value')])
    value_type = fields.Selection([('char','Char'),('integer','Integer'),('float','Float'),('textarea','Text Area'),('color','Color'),('attachment','Attachment'),('date','Date'),('datetime','DateTime')])
    max_value = fields.Integer()
    min_value = fields.Integer()
    required = fields.Boolean(string="Required", default=False)
    uom_id = fields.Many2one('product.uom', 'Unit of Measure',default=_get_default_uom_id, required=True)
    char = fields.Char(string="Custom Char")
    textarea = fields.Text(string="Custom Text")
    color = fields.Integer('Color Index', default=0)
    attachment = fields.Binary(string="Attachment")
    date = fields.Date(string="Select Date", default=fields.Date.context_today, required=True)
    datetime = fields.Datetime(string="Select DateTime", default=fields.Datetime.now, required=True)




    


