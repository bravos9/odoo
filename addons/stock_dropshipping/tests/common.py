# -*- coding: utf-8 -*-

from odoo.tests import common


class TestStockDropshippingCommon(common.SavepointCase):

    def _create_sale_order(cls, partner_id, product, product_qty, uom_id):
        values = {
            'partner_id': partner_id,
            'note': 'Create sale order for product iPad Retina Display',
            'warehouse_id': cls.warehouse.id,
            'pricelist_id': cls.env.ref('product.list0').id,
            'order_line': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'product_uom_qty': product_qty,
                'product_uom': uom_id
             })]
        }
        return cls.env['sale.order'].create(values)

    @classmethod
    def setUpClass(cls):
        super(TestStockDropshippingCommon, cls).setUpClass()

        # Usefull Models.
        cls.ProcurementOrder = cls.env['procurement.order']
        cls.Product = cls.env['product.product']

        cls.Partner = cls.env['res.partner']

        cls.partner_id = cls.env.ref('base.res_partner_3').id
        cls.uom_unit = cls.env.ref('product.product_uom_unit')

        cls.partner = cls.env['res.partner'].create({'name': "Cross dock supplier"})

        # Creating Warehouse
        cls.warehouse = cls.env['stock.warehouse'].create({
            'name': 'WareHouse PickPackShip',
            'code': 'whpps',
            'delivery_steps': 'pick_pack_ship', })
