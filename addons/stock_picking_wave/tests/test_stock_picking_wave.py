# -*- coding: utf-8 -*-

# Author: Tejas Shahu
# Date: 08/14/2017

# from odoo.addons.stock.tests.common import *

from odoo.tests import common


class TestStockPickingWave(common.TransactionCase):

    def setUp(self):
        super(TestStockPickingWave, self).setUp()
        print "test called-----------------------------------------------"
        self.ProductObj = self.env['product.product']
        self.StockQuantObj = self.env['stock.quant']
        self.InvObj = self.env['stock.inventory']
        self.PickingObj = self.env['stock.picking']

        # Product Created A, B, C
        self.productA = self.ProductObj.create({'name': 'Product A', 'type': 'product'})
        self.productB = self.ProductObj.create({'name': 'Product B', 'type': 'product'})
        self.productC = self.ProductObj.create({'name': 'Product C', 'type': 'product'})
        print "\n\nThree Product created Successfully\n\n", self.productA.product_tmpl_id

    def test_warehouse(self):

        print "test a=warehouse called"
        # Warehouses
        self.warehouse_1 = self.env['stock.warehouse'].create({
            'name': 'Base Warehouse',
            # 'reception_steps': 'one_step',
            # 'delivery_steps': 'ship_only',
            'code': 'BWH'})

        # Locations
        self.location_1 = self.env['stock.location'].create({
            'name': 'TestLocation1',
            # 'posx': 3,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        self.location_2 = self.env['stock.location'].create({
            'name': 'TestLocation2',
            # 'posx': 3,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        self.location_3 = self.env['stock.location'].create({
            'name': 'TestLocation3',
            # 'posx': 3,
            'location_id': self.warehouse_1.lot_stock_id.id,
        })

        print "\n\nWarehouse and it's 3 location created\n\n", self.warehouse_1.name

    def test_inventory(self):
        pass