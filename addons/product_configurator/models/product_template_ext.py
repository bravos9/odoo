# -*- coding: utf-8 -*-

from odoo import fields, models, api


class ProductTemplate(models.Model):
	
	_inherit = "product.template"

	variant_mode = fields.Selection(
		[('standard','Standard'),('configurable','Configurable')], 
		help="Standard variants are generated upfront so that you can manage them in your inventory.\n"
		"Configurable variants are generated at the sales when the product is added")
	
