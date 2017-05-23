# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    hsn_code = fields.Char(string="HSN Code", help="Harmonized System Nomenclature")
